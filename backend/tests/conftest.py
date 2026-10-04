import sys
import threading
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402

TOKEN = "test-token"


class FakeDownloader:
    """Simula yt-dlp: avanza por pasos y se puede frenar con `gate`."""

    def __init__(self):
        self.gate = threading.Event()
        self.gate.set()
        self.fail_with: str | None = None
        self.steps = 5

    def __call__(self, job, out_dir, reporter):
        reporter.meta(title="Video de prueba", uploader="Canal de prueba")
        reporter.stage("Extrayendo información", 0)
        for i in range(self.steps):
            self.gate.wait(5)
            reporter.check()
            reporter.stream("video", "video", (i + 1) * 100, self.steps * 100, 1000.0)
            time.sleep(0.01)
        if self.fail_with:
            raise RuntimeError(self.fail_with)
        reporter.stream_done("video", "video", self.steps * 100)
        path = out_dir / "Video de prueba [abc].mp4"
        path.write_bytes(b"x" * 2048)
        return path


def make_settings(tmp_path: Path, **overrides) -> Settings:
    values = dict(
        api_token=TOKEN,
        secret_key="s" * 32,
        data_dir=tmp_path,
        static_dir=tmp_path / "static",
        secure_cookies=False,
        allow_private_urls=True,
        max_concurrent=2,
    )
    values.update(overrides)
    return Settings(_env_file=None, **values)


@pytest.fixture
def downloader():
    return FakeDownloader()


@pytest.fixture
def client(tmp_path, downloader):
    app = create_app(make_settings(tmp_path), downloader=downloader)
    with TestClient(app) as test_client:
        test_client.headers.update({"X-API-Key": TOKEN})
        yield test_client


def wait_for(client: TestClient, job_id: str, status: str, timeout: float = 5.0) -> dict:
    deadline = time.monotonic() + timeout
    last = {}
    while time.monotonic() < deadline:
        last = client.get(f"/api/jobs/{job_id}").json()
        if last["status"] == status:
            return last
        time.sleep(0.02)
    raise AssertionError(f"El job no llegó a '{status}', se quedó en {last.get('status')}")
