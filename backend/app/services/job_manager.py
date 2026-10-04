import itertools
import shutil
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable

from sqlalchemy.engine import Engine
from sqlmodel import Session, select
from yt_dlp.utils import DownloadCancelled

from app.models import Job, utcnow
from app.services import formats, platforms
from app.services.errors import clean_error

ACTIVE_STATUSES = ("waiting", "running", "paused")
RESUMABLE_STATUSES = ("paused", "error")
FINISHED_STATUSES = ("done", "expired", "error")

# (inicio %, fin %) de cada etapa, igual que stagesFor() del prototipo
_VIDEO_RANGES = {"video": (8, 70), "audio": (70, 90), "both": (8, 90)}
_AUDIO_RANGES = {"audio": (8, 85), "both": (8, 85)}


class JobInterrupted(DownloadCancelled):
    def __init__(self, action: str):
        super().__init__(action)
        self.action = action


class Reporter:
    """Canal por el que el downloader le cuenta su avance al manager."""

    def __init__(self, manager: "JobManager", job: Job):
        self._manager = manager
        self.job = job
        self._streams: dict[str, tuple[int, int]] = {}

    def check(self) -> None:
        action = self._manager.pending_action(self.job.id)
        if action:
            raise JobInterrupted(action)

    def meta(self, title: str | None = None, uploader: str | None = None, platform: dict | None = None) -> None:
        if title and self.job.title != title:
            self.job.title = title
        if uploader and not self.job.uploader:
            self.job.uploader = uploader
        if platform and self.job.platform_id == "other":
            self.job.platform_id = platform["id"]
            self.job.mono = platform["mono"]

    def _range(self, kind: str) -> tuple[int, int]:
        ranges = _AUDIO_RANGES if self.job.mode == "audio" else _VIDEO_RANGES
        return ranges.get(kind, ranges["both"])

    def _label(self, kind: str) -> str:
        if self.job.mode == "audio" or kind == "audio":
            return "Descargando audio"
        return "Descargando video"

    def _advance(self, pct: float) -> None:
        self.job.progress = max(self.job.progress, min(pct, 99.0))

    def _refresh_bytes(self) -> None:
        downloaded = sum(d for d, _ in self._streams.values())
        seen_total = sum(t for _, t in self._streams.values())
        self.job.downloaded_bytes = downloaded
        self.job.total_bytes = max(self.job.size_estimate or 0, seen_total) or None

    def stream(self, key: str, kind: str, downloaded: int | None, total: int | None, speed: float | None) -> None:
        self._streams[key] = (int(downloaded or 0), int(total or 0))
        self._refresh_bytes()
        low, high = self._range(kind)
        fraction = min((downloaded or 0) / total, 1.0) if total else 0.0
        self._advance(low + (high - low) * fraction)
        self.job.stage = self._label(kind)
        self.job.speed = speed

    def stream_done(self, key: str, kind: str, total: int | None) -> None:
        size = int(total or self._streams.get(key, (0, 0))[1])
        self._streams[key] = (size, size)
        self._refresh_bytes()
        self._advance(self._range(kind)[1])

    def stage(self, label: str, pct: float) -> None:
        self.job.stage = label
        self.job.speed = None
        self._advance(pct)


Downloader = Callable[[Job, Path, Reporter], Path]


class JobManager:
    def __init__(
        self,
        *,
        engine: Engine,
        downloads_dir: Path,
        downloader: Downloader,
        max_concurrent: int = 2,
        file_ttl_hours: int = 6,
        history_days: int = 30,
    ):
        self._engine = engine
        self._downloads = downloads_dir
        self._downloader = downloader
        self._max_concurrent = max_concurrent
        self._ttl = timedelta(hours=file_ttl_hours)
        self._history = timedelta(days=history_days)

        self._jobs: dict[str, Job] = {}
        self._order: dict[str, int] = {}
        self._flags: dict[str, str] = {}
        self._counter = itertools.count()

        self._lock = threading.RLock()
        self._cond = threading.Condition(self._lock)
        self._executor = ThreadPoolExecutor(max_workers=max_concurrent, thread_name_prefix="clipo-dl")

    # ---------- ciclo de vida ----------

    def start(self) -> None:
        self._downloads.mkdir(parents=True, exist_ok=True)
        with Session(self._engine) as session:
            stored = session.exec(select(Job).order_by(Job.created_at)).all()
            for job in stored:
                session.expunge(job)

        with self._lock:
            for job in stored:
                if job.status in ("running", "waiting"):
                    job.status = "paused"
                    job.speed = None
                    self._persist(job)
                elif job.status == "done" and not self._file_exists(job):
                    job.status = "expired"
                    self._persist(job)
                self._jobs[job.id] = job
                self._order[job.id] = next(self._counter)

    def shutdown(self) -> None:
        with self._lock:
            for job in self._jobs.values():
                if job.status == "running":
                    self._flags[job.id] = "pause"
        self._executor.shutdown(wait=True, cancel_futures=True)

    # ---------- consultas ----------

    def all_jobs(self) -> list[Job]:
        with self._lock:
            return sorted(
                self._jobs.values(),
                key=lambda j: (-j.created_at.timestamp(), self._order.get(j.id, 0)),
            )

    def get(self, job_id: str) -> Job:
        with self._lock:
            job = self._jobs.get(job_id)
        if job is None:
            raise KeyError(job_id)
        return job

    def active_count(self) -> int:
        with self._lock:
            return sum(1 for j in self._jobs.values() if j.status in ("waiting", "running"))

    def pending_action(self, job_id: str) -> str | None:
        return self._flags.get(job_id)

    def file_path(self, job: Job) -> Path | None:
        if job.status != "done" or not job.filename:
            return None
        path = self._downloads / job.id / job.filename
        return path if path.is_file() else None

    def wait(self, job_id: str, timeout: float) -> Job:
        deadline = time.monotonic() + timeout
        with self._cond:
            while True:
                job = self._jobs.get(job_id)
                if job is None:
                    raise KeyError(job_id)
                if job.status not in ("waiting", "running"):
                    return job
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return job
                self._cond.wait(min(remaining, 5))

    # ---------- acciones ----------

    def create(
        self,
        *,
        url: str,
        mode: str = "video",
        quality: str = "1080",
        fps: int | None = None,
        fmt: str = "MP4",
        title: str | None = None,
        uploader: str | None = None,
        thumbnail: str | None = None,
        duration: int | None = None,
        size_estimate: int | None = None,
        source: str = "pwa",
        created_at: datetime | None = None,
    ) -> Job:
        formats.validate_options(mode, quality, fps, fmt)
        platform = platforms.from_url(url)
        job = Job(
            id=uuid.uuid4().hex[:12],
            url=url,
            title=title or url,
            uploader=uploader,
            thumbnail=thumbnail,
            duration=duration,
            platform_id=platform["id"],
            mono=platform["mono"],
            mode=mode,
            quality=quality,
            fps=fps,
            format=fmt,
            spec=formats.spec_label(mode, quality, fps, fmt),
            status="waiting",
            size_estimate=size_estimate,
            total_bytes=size_estimate,
            source=source,
            created_at=created_at or utcnow(),
        )
        with self._lock:
            self._jobs[job.id] = job
            self._order[job.id] = next(self._counter)
            self._persist(job)
            self._schedule()
            self._cond.notify_all()
        return job

    def pause(self, job_id: str) -> Job:
        with self._lock:
            job = self.get(job_id)
            if job.status == "waiting":
                job.status = "paused"
                self._persist(job)
                self._cond.notify_all()
            elif job.status == "running":
                self._flags[job_id] = "pause"
            return job

    def resume(self, job_id: str) -> Job:
        with self._lock:
            job = self.get(job_id)
            if job.status in RESUMABLE_STATUSES:
                job.status = "waiting"
                job.error = None
                job.speed = None
                self._persist(job)
                self._schedule()
                self._cond.notify_all()
            return job

    def pause_all(self) -> None:
        with self._lock:
            for job in list(self._jobs.values()):
                if job.status in ("waiting", "running"):
                    self.pause(job.id)

    def resume_all(self) -> None:
        with self._lock:
            for job in list(self._jobs.values()):
                if job.status == "paused":
                    self.resume(job.id)

    def cancel(self, job_id: str) -> None:
        with self._lock:
            job = self.get(job_id)
            if job.status == "running":
                self._flags[job_id] = "cancel"
                return
            self._remove(job)

    def clear_finished(self) -> int:
        with self._lock:
            targets = [j for j in self._jobs.values() if j.status in FINISHED_STATUSES]
            for job in targets:
                self._remove(job)
            return len(targets)

    def cleanup(self) -> None:
        now = utcnow()
        with self._lock:
            for job in list(self._jobs.values()):
                if not job.finished_at:
                    continue
                age = now - job.finished_at
                if job.status in ("done", "error") and age > self._ttl:
                    shutil.rmtree(self._downloads / job.id, ignore_errors=True)
                    if job.status == "done":
                        job.status = "expired"
                        self._persist(job)
                if job.status in ("expired", "error") and age > self._history:
                    self._remove(job)
            self._cond.notify_all()

        if self._downloads.is_dir():
            known = set(self._jobs)
            for folder in self._downloads.iterdir():
                stale = time.time() - folder.stat().st_mtime > 86400
                if folder.is_dir() and folder.name not in known and stale:
                    shutil.rmtree(folder, ignore_errors=True)

    # ---------- internos ----------

    def _persist(self, job: Job) -> None:
        with Session(self._engine) as session:
            session.merge(job)
            session.commit()

    def _delete_row(self, job_id: str) -> None:
        with Session(self._engine) as session:
            row = session.get(Job, job_id)
            if row:
                session.delete(row)
                session.commit()

    def _file_exists(self, job: Job) -> bool:
        return bool(job.filename) and (self._downloads / job.id / job.filename).is_file()

    def _remove(self, job: Job) -> None:
        self._jobs.pop(job.id, None)
        self._order.pop(job.id, None)
        self._flags.pop(job.id, None)
        shutil.rmtree(self._downloads / job.id, ignore_errors=True)
        self._delete_row(job.id)
        self._schedule()
        self._cond.notify_all()

    def _schedule(self) -> None:
        running = sum(1 for j in self._jobs.values() if j.status == "running")
        free = self._max_concurrent - running
        if free <= 0:
            return
        waiting = sorted(
            (j for j in self._jobs.values() if j.status == "waiting"),
            key=lambda j: self._order.get(j.id, 0),
        )
        for job in waiting[:free]:
            job.status = "running"
            job.stage = "Extrayendo información"
            self._persist(job)
            self._executor.submit(self._run, job.id)

    def _run(self, job_id: str) -> None:
        job = self._jobs.get(job_id)
        if job is None:
            return
        out_dir = self._downloads / job_id
        out_dir.mkdir(parents=True, exist_ok=True)
        try:
            path = self._downloader(job, out_dir, Reporter(self, job))
        except Exception as exc:
            self._finish_failed(job, exc)
        else:
            self._finish_ok(job, path)

    def _finish_ok(self, job: Job, path: Path) -> None:
        with self._lock:
            if self._flags.pop(job.id, None) == "cancel":
                self._remove(job)
                return
            size = path.stat().st_size
            job.status = "done"
            job.progress = 100.0
            job.stage = "Listo"
            job.filename = path.name
            job.size_bytes = size
            job.total_bytes = size
            job.downloaded_bytes = size
            job.speed = None
            job.finished_at = utcnow()
            self._persist(job)
            self._schedule()
            self._cond.notify_all()

    def _finish_failed(self, job: Job, exc: Exception) -> None:
        with self._lock:
            action = self._flags.pop(job.id, None)
            if action is None and isinstance(exc, JobInterrupted):
                action = exc.action

            if action == "cancel":
                self._remove(job)
                return

            job.speed = None
            if action == "pause":
                job.status = "paused"
            else:
                job.status = "error"
                job.error = clean_error(exc)
                job.finished_at = utcnow()
            self._persist(job)
            self._schedule()
            self._cond.notify_all()
