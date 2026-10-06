import os
import shutil
import subprocess
import threading
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.services import thumbnails

from tests.conftest import TOKEN, make_settings, wait_for

pytestmark = pytest.mark.skipif(not (shutil.which("ffmpeg") and shutil.which("ffprobe")), reason="ffmpeg no disponible")

URL = "https://example.com/watch?v=1"
JPEG_MAGIC = b"\xff\xd8\xff"


def ffmpeg(*args):
    subprocess.run(["ffmpeg", "-y", "-v", "error", *args], check=True, capture_output=True)


def jpeg_width(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout
    return int(out.strip())


@pytest.fixture
def make_video(tmp_path):
    def _make(name="clip.mp4", seconds=3):
        path = tmp_path / name
        ffmpeg("-f", "lavfi", "-i", f"testsrc=duration={seconds}:size=1280x720:rate=15",
               "-f", "lavfi", "-i", "sine=frequency=440", "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(path))
        return path
    return _make


@pytest.fixture
def image_server(tmp_path):
    root = tmp_path / "www"
    root.mkdir()
    ffmpeg("-f", "lavfi", "-i", "testsrc=size=1920x1080:rate=1", "-frames:v", "1", str(root / "foto.jpg"))
    (root / "basura.jpg").write_bytes(b"esto no es una imagen")
    (root / "enorme.jpg").write_bytes(os.urandom(thumbnails.MAX_BYTES + 1000))

    class Quiet(SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Quiet, directory=str(root)))
    server.handle_error = lambda *args: None
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()


# ---------- funciones sueltas ----------

def test_from_video_creates_a_small_jpeg(tmp_path, make_video):
    dest = tmp_path / "thumb.jpg"
    assert thumbnails.from_video(make_video(), dest, duration=3)
    assert dest.read_bytes().startswith(JPEG_MAGIC)
    assert jpeg_width(dest) == thumbnails.WIDTH
    assert not list(tmp_path.glob("*.tmp.jpg"))


def test_from_video_works_even_with_a_very_short_clip(tmp_path, make_video):
    dest = tmp_path / "thumb.jpg"
    assert thumbnails.from_video(make_video("corto.mp4", seconds=1), dest, duration=1)
    assert dest.is_file()


def test_from_video_fails_cleanly_on_a_broken_file(tmp_path):
    broken = tmp_path / "roto.mp4"
    broken.write_bytes(b"nada")
    dest = tmp_path / "thumb.jpg"
    assert thumbnails.from_video(broken, dest) is False
    assert not dest.exists()


def test_fetch_remote_downloads_and_shrinks_the_image(tmp_path, image_server):
    dest = tmp_path / "thumb.jpg"
    assert thumbnails.fetch_remote(f"{image_server}/foto.jpg", dest, allow_private=True)
    assert dest.read_bytes().startswith(JPEG_MAGIC)
    assert jpeg_width(dest) == thumbnails.WIDTH
    assert not list(tmp_path.glob("*.src")) and not list(tmp_path.glob("*.tmp.jpg"))


def test_fetch_remote_refuses_private_addresses_by_default(tmp_path, image_server):
    dest = tmp_path / "thumb.jpg"
    assert thumbnails.fetch_remote(f"{image_server}/foto.jpg", dest, allow_private=False) is False
    assert not dest.exists()


def test_fetch_remote_rejects_files_that_are_not_images(tmp_path, image_server):
    dest = tmp_path / "thumb.jpg"
    assert thumbnails.fetch_remote(f"{image_server}/basura.jpg", dest, allow_private=True) is False
    assert not dest.exists() and not list(tmp_path.glob("*.src"))


def test_fetch_remote_rejects_oversized_downloads(tmp_path, image_server):
    dest = tmp_path / "thumb.jpg"
    assert thumbnails.fetch_remote(f"{image_server}/enorme.jpg", dest, allow_private=True) is False
    assert not dest.exists()


def test_fetch_remote_survives_a_missing_file_and_a_dead_host(tmp_path, image_server):
    dest = tmp_path / "thumb.jpg"
    assert thumbnails.fetch_remote(f"{image_server}/no-existe.jpg", dest, allow_private=True) is False
    assert thumbnails.fetch_remote("http://127.0.0.1:9/x.jpg", dest, allow_private=True) is False


# ---------- por la API ----------

class VideoDownloader:
    def __init__(self, source):
        self.source = source

    def __call__(self, job, out_dir, reporter):
        reporter.stream("v", "video", 1, 1, 1.0)
        reporter.stream_done("v", "video", 1)
        path = out_dir / "video.mp4"
        shutil.copy(self.source, path)
        return path


def make_client(tmp_path, downloader):
    app = create_app(make_settings(tmp_path), downloader=downloader)
    return TestClient(app, headers={"X-API-Key": TOKEN})


def test_finished_video_gets_a_frame_as_thumbnail(tmp_path, make_video):
    with make_client(tmp_path / "data", VideoDownloader(make_video())) as client:
        job = client.post("/api/jobs", json={"url": URL, "duration": 3}).json()[0]
        done = wait_for(client, job["id"], "done")
        assert done["has_thumbnail"] is True

        response = client.get(f"/api/jobs/{job['id']}/thumbnail")
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/jpeg"
        assert "private" in response.headers["cache-control"]
        assert response.content.startswith(JPEG_MAGIC)


def test_thumbnail_needs_auth_and_404s_when_there_is_none(tmp_path, downloader):
    with make_client(tmp_path / "data", downloader) as client:
        job = client.post("/api/jobs", json={"url": URL}).json()[0]
        done = wait_for(client, job["id"], "done")
        assert done["has_thumbnail"] is False
        assert client.get(f"/api/jobs/{job['id']}/thumbnail").status_code == 404
        assert client.get("/api/jobs/nope/thumbnail").status_code == 404
        assert TestClient(client.app).get(f"/api/jobs/{job['id']}/thumbnail").status_code == 401


def test_site_thumbnail_is_fetched_when_the_job_is_created(tmp_path, downloader, image_server):
    with make_client(tmp_path / "data", downloader) as client:
        job = client.post("/api/jobs", json={"url": URL, "thumbnail": f"{image_server}/foto.jpg"}).json()[0]
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and not client.get(f"/api/jobs/{job['id']}").json()["has_thumbnail"]:
            time.sleep(0.05)
        assert client.get(f"/api/jobs/{job['id']}").json()["has_thumbnail"] is True
        assert client.get(f"/api/jobs/{job['id']}/thumbnail").content.startswith(JPEG_MAGIC)


def test_audio_jobs_do_not_get_a_frame(tmp_path, make_video):
    with make_client(tmp_path / "data", VideoDownloader(make_video())) as client:
        job = client.post("/api/jobs", json={"url": URL, "mode": "audio", "quality": "320", "format": "MP3"}).json()[0]
        assert wait_for(client, job["id"], "done")["has_thumbnail"] is False


def test_thumbnail_survives_file_expiry_and_goes_away_with_the_job(tmp_path, make_video):
    settings = make_settings(tmp_path / "data", file_ttl_hours=0)
    app = create_app(settings, downloader=VideoDownloader(make_video()))
    with TestClient(app, headers={"X-API-Key": TOKEN}) as client:
        job = client.post("/api/jobs", json={"url": URL, "duration": 3}).json()[0]
        wait_for(client, job["id"], "done")
        time.sleep(0.05)
        app.state.manager.cleanup()

        expired = client.get(f"/api/jobs/{job['id']}").json()
        assert expired["status"] == "expired" and expired["has_thumbnail"] is True
        assert client.get(f"/api/jobs/{job['id']}/thumbnail").status_code == 200

        thumb = tmp_path / "data" / "thumbs" / f"{job['id']}.jpg"
        assert thumb.is_file()
        client.delete(f"/api/jobs/{job['id']}")
        assert not thumb.exists()


def test_clearing_the_library_deletes_every_thumbnail(tmp_path, make_video):
    with make_client(tmp_path / "data", VideoDownloader(make_video())) as client:
        ids = [client.post("/api/jobs", json={"url": URL, "duration": 3}).json()[0]["id"] for _ in range(2)]
        for job_id in ids:
            wait_for(client, job_id, "done")
        client.delete("/api/jobs", params={"status": "done"})
        assert list((tmp_path / "data" / "thumbs").glob("*.jpg")) == []


def test_cleanup_removes_only_old_orphan_thumbnails(tmp_path, downloader):
    app = create_app(make_settings(tmp_path / "data"), downloader=downloader)
    with TestClient(app, headers={"X-API-Key": TOKEN}):
        folder = tmp_path / "data" / "thumbs"
        old, fresh = folder / "viejo.jpg", folder / "reciente.jpg"
        old.write_bytes(JPEG_MAGIC)
        fresh.write_bytes(JPEG_MAGIC)
        two_days_ago = time.time() - 2 * 86400
        os.utime(old, (two_days_ago, two_days_ago))

        app.state.manager.cleanup()

        assert not old.exists() and fresh.exists()
