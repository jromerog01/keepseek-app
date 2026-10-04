from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Job(SQLModel, table=True):
    id: str = Field(primary_key=True)
    url: str
    title: str
    uploader: str | None = None
    thumbnail: str | None = None
    duration: int | None = None

    platform_id: str = "other"
    mono: str = "+"

    mode: str = "video"
    quality: str = "1080"
    fps: int | None = None
    format: str = "MP4"
    spec: str = ""

    status: str = "waiting"
    error: str | None = None
    progress: float = 0.0
    stage: str | None = None
    downloaded_bytes: int = 0
    total_bytes: int | None = None
    size_estimate: int | None = None
    speed: float | None = None

    filename: str | None = None
    size_bytes: int | None = None
    source: str = "pwa"

    created_at: datetime = Field(default_factory=utcnow)
    finished_at: datetime | None = None
