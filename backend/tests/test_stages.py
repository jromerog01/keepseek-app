import threading

from fastapi.testclient import TestClient

from app.main import create_app
from app.services.stages import StageTracker

from tests.conftest import TOKEN, make_settings, wait_for

URL = "https://example.com/watch?v=1"


def by_key(stages):
    return {s["key"]: s for s in stages}


# ---------- el rastreador por sí solo ----------

def test_video_mode_starts_with_info_active_and_the_rest_pending():
    tracker = StageTracker("video")
    tracker.begin("info")
    states = [(s["key"], s["state"]) for s in tracker.snapshot()]
    assert states == [("info", "active"), ("video", "pending"), ("audio", "pending"), ("merge", "pending")]


def test_audio_mode_has_no_video_or_merge_stage():
    assert [s["key"] for s in StageTracker("audio").snapshot()] == ["info", "audio", "convert"]


def test_progress_only_moves_forward_and_is_capped_below_100():
    tracker = StageTracker("video")
    tracker.progress("video", 40)
    tracker.progress("video", 20)
    tracker.progress("video", 150)
    assert by_key(tracker.snapshot())["video"]["pct"] == 99.9


def test_finish_sets_100_and_skip_never_overrides_a_finished_stage():
    tracker = StageTracker("video")
    tracker.finish("video")
    tracker.skip("video")
    stage = by_key(tracker.snapshot())["video"]
    assert (stage["state"], stage["pct"]) == ("done", 100.0)


def test_merge_and_convert_have_no_percentage_while_running():
    tracker = StageTracker("video")
    tracker.begin("merge")
    assert by_key(tracker.snapshot())["merge"]["pct"] is None


def test_settle_finishes_running_stages_and_skips_the_ones_that_never_ran():
    tracker = StageTracker("video")
    tracker.finish("video")
    tracker.begin("merge")
    tracker.settle()
    result = by_key(tracker.snapshot())
    assert result["merge"]["state"] == "done" and result["merge"]["pct"] == 100.0
    assert result["audio"]["state"] == "skipped" and result["audio"]["pct"] is None


# ---------- de punta a punta por la API ----------

class SteppedDownloader:
    """Se detiene en cada etapa para poder consultar el avance a medio camino."""

    STEPS = ("video", "audio", "merge")

    def __init__(self):
        self.reached = {n: threading.Event() for n in self.STEPS}
        self.release = {n: threading.Event() for n in self.STEPS}

    def _stop(self, name):
        self.reached[name].set()
        self.release[name].wait(5)

    def __call__(self, job, out_dir, reporter):
        reporter.stream("v", "video", 50, 100, 1000.0)
        self._stop("video")
        reporter.stream_done("v", "video", 100)
        reporter.stream("a", "audio", 25, 100, 500.0)
        self._stop("audio")
        reporter.stream_done("a", "audio", 100)
        reporter.stage("Uniendo audio y video", 90, key="merge")
        self._stop("merge")
        reporter.stage_done("merge")
        path = out_dir / "v.mp4"
        path.write_bytes(b"x")
        return path


def test_each_stage_reports_its_own_progress_through_the_api(tmp_path):
    stepped = SteppedDownloader()
    with TestClient(create_app(make_settings(tmp_path), downloader=stepped), headers={"X-API-Key": TOKEN}) as client:
        job = client.post("/api/jobs", json={"url": URL}).json()[0]
        get = lambda: by_key(client.get(f"/api/jobs/{job['id']}").json()["stages"])

        assert stepped.reached["video"].wait(5)
        s = get()
        assert (s["info"]["state"], s["video"]["state"], s["video"]["pct"]) == ("done", "active", 50.0)
        assert (s["audio"]["state"], s["merge"]["state"]) == ("pending", "pending")
        stepped.release["video"].set()

        assert stepped.reached["audio"].wait(5)
        s = get()
        assert (s["video"]["state"], s["video"]["pct"]) == ("done", 100.0)
        assert (s["audio"]["state"], s["audio"]["pct"]) == ("active", 25.0)
        stepped.release["audio"].set()

        assert stepped.reached["merge"].wait(5)
        s = get()
        assert s["audio"]["state"] == "done"
        assert (s["merge"]["state"], s["merge"]["pct"]) == ("active", None)
        stepped.release["merge"].set()

        wait_for(client, job["id"], "done")
        assert {k: v["state"] for k, v in get().items()} == {k: "done" for k in ("info", "video", "audio", "merge")}


def test_single_stream_download_skips_audio_and_merge(client, downloader):
    class Single:
        def __call__(self, job, out_dir, reporter):
            reporter.stream("v", "both", 10, 100, 1.0)
            reporter.stream_done("v", "both", 100)
            path = out_dir / "v.mp4"
            path.write_bytes(b"x")
            return path

    client.app.state.manager._downloader = Single()
    job = client.post("/api/jobs", json={"url": URL}).json()[0]
    wait_for(client, job["id"], "done")
    states = {k: v["state"] for k, v in by_key(client.get(f"/api/jobs/{job['id']}").json()["stages"]).items()}
    assert states == {"info": "done", "video": "done", "audio": "skipped", "merge": "skipped"}


def test_audio_job_lists_info_audio_and_convert(client):
    class Audio:
        def __call__(self, job, out_dir, reporter):
            reporter.stream("a", "audio", 50, 100, 1.0)
            reporter.stream_done("a", "audio", 100)
            reporter.stage("Convirtiendo", 85, key="convert")
            reporter.stage_done("convert")
            path = out_dir / "a.mp3"
            path.write_bytes(b"x")
            return path

    client.app.state.manager._downloader = Audio()
    job = client.post("/api/jobs", json={"url": URL, "mode": "audio", "quality": "320", "format": "MP3"}).json()[0]
    wait_for(client, job["id"], "done")
    stages = client.get(f"/api/jobs/{job['id']}").json()["stages"]
    assert [(s["key"], s["state"]) for s in stages] == [("info", "done"), ("audio", "done"), ("convert", "done")]


def test_conversion_stage_appears_with_its_percentage(client):
    seen = {}

    class Converting:
        def __call__(self, job, out_dir, reporter):
            reporter.stream("v", "video", 100, 100, 1.0)
            reporter.stream_done("v", "video", 100)
            reporter.begin_conversion()
            reporter.conversion_progress(40)
            seen["stages"] = by_key(client.app.state.manager.stages_for(job.id))
            seen["progress"] = job.progress
            reporter.conversion_progress(100)
            reporter.stage_done("convert_ios")
            path = out_dir / "v.mp4"
            path.write_bytes(b"x")
            return path

    client.app.state.manager._downloader = Converting()
    job = client.post("/api/jobs", json={"url": URL}).json()[0]
    wait_for(client, job["id"], "done")
    stage = seen["stages"]["convert_ios"]
    assert (stage["label"], stage["state"], stage["pct"]) == ("Convirtiendo para iPhone", "active", 40.0)
    assert 92 < seen["progress"] < 99
    assert [s["key"] for s in client.get(f"/api/jobs/{job['id']}").json()["stages"]][-1] == "convert_ios"


def test_jobs_loaded_after_a_restart_have_no_live_stages(client):
    job = client.post("/api/jobs", json={"url": URL}).json()[0]
    wait_for(client, job["id"], "done")
    client.app.state.manager._trackers.clear()
    assert client.get(f"/api/jobs/{job['id']}").json()["stages"] is None
