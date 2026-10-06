import time

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.db import make_engine
from app.main import create_app
from app.models import Job, utcnow

from tests.conftest import TOKEN, make_settings, wait_for

URL = "https://example.com/watch?v=1"


def create(client, **body):
    payload = {"url": URL, **body}
    response = client.post("/api/jobs", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


# ---------- auth ----------

def test_health_needs_no_auth(client):
    anonymous = TestClient(client.app)
    assert anonymous.get("/api/health").json() == {"ok": True, "active_jobs": 0}


def test_system_reports_tool_versions(client):
    import shutil

    data = client.get("/api/system").json()
    assert data["ytdlp_version"]
    assert data["file_ttl_hours"] == 6
    if shutil.which("ffmpeg"):
        assert data["ffmpeg"].startswith("ffmpeg")


def test_protected_routes_reject_missing_or_wrong_key(client):
    anonymous = TestClient(client.app)
    assert anonymous.get("/api/jobs").status_code == 401
    assert anonymous.get("/api/jobs", headers={"X-API-Key": "nope"}).status_code == 401
    assert anonymous.post("/api/analyze", json={"url": URL}).status_code == 401
    assert client.get("/api/jobs").status_code == 200


def test_login_sets_cookie_that_authorizes(client):
    browser = TestClient(client.app)
    assert browser.post("/api/auth/login", json={"token": "mal"}).status_code == 401
    assert browser.get("/api/auth/me").status_code == 401

    response = browser.post("/api/auth/login", json={"token": TOKEN})
    assert response.status_code == 200
    assert "httponly" in response.headers["set-cookie"].lower()
    assert browser.get("/api/auth/me").status_code == 200
    assert browser.get("/api/jobs").status_code == 200

    browser.post("/api/auth/logout")
    assert browser.get("/api/auth/me").status_code == 401


def test_forged_cookie_is_rejected(client):
    browser = TestClient(client.app)
    browser.cookies.set("clipo_session", "falsa.firma.aqui")
    assert browser.get("/api/jobs").status_code == 401


def test_login_is_rate_limited(client):
    browser = TestClient(client.app)
    for _ in range(10):
        assert browser.post("/api/auth/login", json={"token": "mal"}).status_code == 401
    assert browser.post("/api/auth/login", json={"token": TOKEN}).status_code == 429


# ---------- ciclo de vida ----------

def test_job_runs_to_completion_and_serves_file(client):
    job = create(client)[0]
    assert job["status"] in ("waiting", "running")

    done = client.get(f"/api/jobs/{job['id']}/wait", params={"timeout": 5}).json()
    assert done["status"] == "done"
    assert done["progress"] == 100
    assert done["title"] == "Video de prueba"
    assert done["uploader"] == "Canal de prueba"
    assert done["size_bytes"] == 2048
    assert done["file_available"] is True
    assert done["expires_at"].endswith("Z")

    file = client.get(f"/api/jobs/{job['id']}/file")
    assert file.status_code == 200
    assert file.content == b"x" * 2048
    assert "attachment" in file.headers["content-disposition"]


def test_file_is_409_before_done(client, downloader):
    downloader.gate.clear()
    job = create(client)[0]
    wait_for(client, job["id"], "running")
    assert client.get(f"/api/jobs/{job['id']}/file").status_code == 409
    downloader.gate.set()


def test_wait_returns_current_state_on_timeout(client, downloader):
    downloader.gate.clear()
    job = create(client)[0]
    started = time.monotonic()
    result = client.get(f"/api/jobs/{job['id']}/wait", params={"timeout": 1}).json()
    assert result["status"] == "running"
    assert 0.9 < time.monotonic() - started < 3
    downloader.gate.set()


def test_pause_and_resume(client, downloader):
    downloader.gate.clear()
    job = create(client)[0]
    wait_for(client, job["id"], "running")

    client.post(f"/api/jobs/{job['id']}/pause")
    downloader.gate.set()
    wait_for(client, job["id"], "paused")

    client.post(f"/api/jobs/{job['id']}/resume")
    assert wait_for(client, job["id"], "done")["file_available"] is True


def test_cancel_running_job_removes_it_and_its_files(client, downloader, tmp_path):
    downloader.gate.clear()
    job = create(client)[0]
    wait_for(client, job["id"], "running")

    assert client.delete(f"/api/jobs/{job['id']}").status_code == 204
    downloader.gate.set()

    deadline = time.monotonic() + 5
    while time.monotonic() < deadline and client.get(f"/api/jobs/{job['id']}").status_code != 404:
        time.sleep(0.02)
    assert client.get(f"/api/jobs/{job['id']}").status_code == 404
    assert not (tmp_path / "downloads" / job["id"]).exists()
    assert client.get("/api/jobs").json() == []


def test_concurrency_limit_queues_the_rest(tmp_path, downloader):
    downloader.gate.clear()
    app = create_app(make_settings(tmp_path, max_concurrent=1), downloader=downloader)
    with TestClient(app, headers={"X-API-Key": TOKEN}) as client:
        first = create(client)[0]
        second = create(client)[0]
        wait_for(client, first["id"], "running")
        assert client.get(f"/api/jobs/{second['id']}").json()["status"] == "waiting"

        client.delete(f"/api/jobs/{second['id']}")
        assert client.get(f"/api/jobs/{second['id']}").status_code == 404
        downloader.gate.set()
        wait_for(client, first["id"], "done")


def test_waiting_job_starts_when_a_slot_frees_up(tmp_path, downloader):
    downloader.gate.clear()
    app = create_app(make_settings(tmp_path, max_concurrent=1), downloader=downloader)
    with TestClient(app, headers={"X-API-Key": TOKEN}) as client:
        first = create(client)[0]
        second = create(client)[0]
        wait_for(client, first["id"], "running")
        downloader.gate.set()
        wait_for(client, first["id"], "done")
        wait_for(client, second["id"], "done")


def test_failure_marks_error_and_can_be_retried(client, downloader):
    downloader.fail_with = "ERROR: [youtube] abc: Video unavailable"
    job = create(client)[0]
    failed = wait_for(client, job["id"], "error")
    assert failed["error"] == "Video unavailable"

    downloader.fail_with = None
    client.post(f"/api/jobs/{job['id']}/resume")
    assert wait_for(client, job["id"], "done")["error"] is None


def test_playlist_items_create_one_job_each_in_order(client):
    items = [{"url": f"https://example.com/v{i}", "title": f"Video {i}"} for i in range(1, 4)]
    jobs = create(client, items=items)
    assert [j["url"] for j in jobs] == [i["url"] for i in items]
    listed = client.get("/api/jobs").json()
    assert [j["url"] for j in listed] == [i["url"] for i in items]


def test_quick_uses_iphone_friendly_preset(client):
    response = client.post("/api/quick", json={"url": URL})
    assert response.status_code == 201
    job = response.json()
    assert (job["mode"], job["quality"], job["format"], job["source"]) == ("video", "1080", "MP4", "shortcut")
    assert job["spec"] == "1080p · MP4"


def test_quick_audio_preset(client):
    job = client.post("/api/quick", json={"url": URL, "mode": "audio"}).json()
    assert (job["mode"], job["quality"], job["format"]) == ("audio", "320", "MP3")


def test_invalid_options_are_rejected(client):
    assert client.post("/api/jobs", json={"url": URL, "quality": "999"}).status_code == 422
    assert client.post("/api/jobs", json={"url": URL, "mode": "audio", "format": "MP4", "quality": "320"}).status_code == 422
    assert client.post("/api/jobs", json={"url": "ftp://x/y"}).status_code == 400


def test_private_urls_are_blocked_by_default(tmp_path, downloader):
    app = create_app(make_settings(tmp_path, allow_private_urls=False), downloader=downloader)
    with TestClient(app, headers={"X-API-Key": TOKEN}) as client:
        response = client.post("/api/jobs", json={"url": "http://192.168.1.1/admin"})
        assert response.status_code == 400
        assert client.post("/api/analyze", json={"url": "http://localhost:8000"}).status_code == 400


def test_clear_finished_removes_done_jobs(client):
    job = create(client)[0]
    wait_for(client, job["id"], "done")
    assert client.delete("/api/jobs", params={"status": "done"}).json() == {"removed": 1}
    assert client.get("/api/jobs").json() == []


def test_clear_finished_keeps_error_jobs_in_queue(client, downloader):
    downloader.fail_with = "ERROR: [youtube] abc: Video unavailable"
    failed = create(client)[0]
    wait_for(client, failed["id"], "error")

    downloader.fail_with = None
    done = create(client)[0]
    wait_for(client, done["id"], "done")

    assert client.delete("/api/jobs", params={"status": "done"}).json() == {"removed": 1}
    listed = client.get("/api/jobs").json()
    assert [job["id"] for job in listed] == [failed["id"]]
    assert listed[0]["status"] == "error"


def test_pause_all_and_resume_all(client, downloader):
    downloader.gate.clear()
    a, b = create(client)[0], create(client)[0]
    wait_for(client, a["id"], "running")
    wait_for(client, b["id"], "running")

    client.post("/api/jobs/pause-all")
    downloader.gate.set()
    wait_for(client, a["id"], "paused")
    wait_for(client, b["id"], "paused")

    client.post("/api/jobs/resume-all")
    wait_for(client, a["id"], "done")
    wait_for(client, b["id"], "done")


def test_unknown_job_is_404(client):
    assert client.get("/api/jobs/nope").status_code == 404
    assert client.post("/api/jobs/nope/pause").status_code == 404
    assert client.delete("/api/jobs/nope").status_code == 404


# ---------- persistencia y limpieza ----------

def test_interrupted_jobs_come_back_paused(tmp_path, downloader):
    settings = make_settings(tmp_path)
    engine = make_engine(settings.db_path)
    with Session(engine) as session:
        for job_id, status in (("run1", "running"), ("wait1", "waiting")):
            session.add(Job(id=job_id, url=URL, title="x", status=status, created_at=utcnow()))
        session.commit()

    app = create_app(settings, downloader=downloader)
    with TestClient(app, headers={"X-API-Key": TOKEN}) as client:
        statuses = {j["id"]: j["status"] for j in client.get("/api/jobs").json()}
        assert statuses == {"run1": "paused", "wait1": "paused"}


def test_done_jobs_survive_restart_and_missing_files_expire(tmp_path, downloader):
    settings = make_settings(tmp_path)
    with TestClient(create_app(settings, downloader=downloader), headers={"X-API-Key": TOKEN}) as client:
        kept = create(client)[0]
        lost = create(client)[0]
        wait_for(client, kept["id"], "done")
        wait_for(client, lost["id"], "done")

    for file in (tmp_path / "downloads" / lost["id"]).iterdir():
        file.unlink()

    with TestClient(create_app(settings, downloader=downloader), headers={"X-API-Key": TOKEN}) as client:
        assert client.get(f"/api/jobs/{kept['id']}").json()["status"] == "done"
        assert client.get(f"/api/jobs/{lost['id']}").json()["status"] == "expired"
        assert client.get(f"/api/jobs/{lost['id']}/file").status_code == 410


def test_cleanup_expires_old_files(tmp_path, downloader):
    settings = make_settings(tmp_path, file_ttl_hours=0)
    with TestClient(create_app(settings, downloader=downloader), headers={"X-API-Key": TOKEN}) as client:
        job = create(client)[0]
        wait_for(client, job["id"], "done")
        time.sleep(0.05)
        client.app.state.manager.cleanup()

        assert client.get(f"/api/jobs/{job['id']}").json()["status"] == "expired"
        assert client.get(f"/api/jobs/{job['id']}/file").status_code == 410
        assert not (tmp_path / "downloads" / job["id"]).exists()


# ---------- frontend estático ----------

def test_spa_fallback_and_static_files(tmp_path, downloader):
    static = tmp_path / "static"
    (static / "assets").mkdir(parents=True)
    (static / "index.html").write_text("<html>clipo</html>")
    (static / "assets" / "app.js").write_text("console.log(1)")
    (tmp_path / "secreto.txt").write_text("no debería salir")

    app = create_app(make_settings(tmp_path), downloader=downloader)
    with TestClient(app) as client:
        index = client.get("/")
        assert index.text == "<html>clipo</html>"
        assert index.headers["cache-control"] == "no-cache"

        assert client.get("/biblioteca/ruta/profunda").text == "<html>clipo</html>"

        asset = client.get("/assets/app.js")
        assert asset.text == "console.log(1)"
        assert "immutable" in asset.headers["cache-control"]

        assert "no debería salir" not in client.get("/../secreto.txt").text
        assert "no debería salir" not in client.get("/%2e%2e/secreto.txt").text
        assert client.get("/api/no-existe").status_code == 404


def test_app_refuses_to_start_without_secrets(tmp_path):
    import pytest

    with pytest.raises(RuntimeError):
        create_app(make_settings(tmp_path, api_token=""))


def test_file_supports_partial_downloads_so_any_size_can_resume(client):
    job = create(client)[0]
    wait_for(client, job["id"], "done")

    full = client.get(f"/api/jobs/{job['id']}/file")
    assert full.headers["accept-ranges"] == "bytes" and len(full.content) == 2048

    part = client.get(f"/api/jobs/{job['id']}/file", headers={"Range": "bytes=100-199"})
    assert part.status_code == 206
    assert part.headers["content-range"] == "bytes 100-199/2048"
    assert part.content == full.content[100:200]

    tail = client.get(f"/api/jobs/{job['id']}/file", headers={"Range": "bytes=2000-"})
    assert tail.status_code == 206 and tail.content == full.content[2000:]
