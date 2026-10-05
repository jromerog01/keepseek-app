from datetime import datetime, timedelta
from typing import Literal

from pydantic import BaseModel, Field

from app.models import Job

Mode = Literal["video", "audio"]
Format = Literal["MP4", "WEBM", "MKV", "MP3", "M4A", "OPUS"]


class AnalyzeRequest(BaseModel):
    url: str = Field(min_length=1, max_length=2048)


class JobItem(BaseModel):
    url: str = Field(min_length=1, max_length=2048)
    title: str | None = Field(default=None, max_length=300)
    duration: int | None = None


class JobCreate(BaseModel):
    url: str = Field(min_length=1, max_length=2048)
    mode: Mode = "video"
    quality: str = "1080"
    fps: int | None = None
    format: Format = "MP4"
    title: str | None = Field(default=None, max_length=300)
    uploader: str | None = Field(default=None, max_length=200)
    thumbnail: str | None = Field(default=None, max_length=2048)
    duration: int | None = None
    size_estimate: int | None = None
    items: list[JobItem] | None = Field(default=None, max_length=200)


class QuickRequest(BaseModel):
    url: str = Field(min_length=1, max_length=2048)
    mode: Mode = "video"


class LoginRequest(BaseModel):
    token: str = Field(min_length=1, max_length=256)


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() + "Z" if value else None


class StageOut(BaseModel):
    key: str
    label: str
    state: str
    pct: float | None


class JobOut(BaseModel):
    id: str
    url: str
    title: str
    uploader: str | None
    thumbnail: str | None
    duration: int | None
    platform_id: str
    mono: str
    mode: str
    quality: str
    fps: int | None
    format: str
    spec: str
    status: str
    error: str | None
    progress: float
    stage: str | None
    downloaded_bytes: int
    total_bytes: int | None
    size_bytes: int | None
    speed: float | None
    eta: int | None
    source: str
    created_at: str
    finished_at: str | None
    expires_at: str | None
    file_available: bool
    stages: list[StageOut] | None = None

    @classmethod
    def from_job(cls, job: Job, ttl_hours: int, stages: list[dict] | None = None) -> "JobOut":
        eta = None
        if job.status == "running" and job.speed and job.total_bytes:
            remaining = max(job.total_bytes - job.downloaded_bytes, 0)
            eta = int(remaining / job.speed)

        expires_at = None
        if job.status == "done" and job.finished_at:
            expires_at = _iso(job.finished_at + timedelta(hours=ttl_hours))

        return cls(
            id=job.id,
            url=job.url,
            title=job.title,
            uploader=job.uploader,
            thumbnail=job.thumbnail,
            duration=job.duration,
            platform_id=job.platform_id,
            mono=job.mono,
            mode=job.mode,
            quality=job.quality,
            fps=job.fps,
            format=job.format,
            spec=job.spec,
            status=job.status,
            error=job.error,
            progress=round(job.progress, 1),
            stage=job.stage,
            downloaded_bytes=job.downloaded_bytes,
            total_bytes=job.total_bytes,
            size_bytes=job.size_bytes,
            speed=job.speed,
            eta=eta,
            source=job.source,
            created_at=_iso(job.created_at),
            finished_at=_iso(job.finished_at),
            expires_at=expires_at,
            file_available=job.status == "done" and bool(job.filename),
            stages=stages,
        )
