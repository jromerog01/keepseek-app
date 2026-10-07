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
    # "admin" (token original) o el id de la invitación que la creó
    owner: str = Field(default="admin", index=True)
    device: str | None = None

    created_at: datetime = Field(default_factory=utcnow)
    finished_at: datetime | None = None


class Invite(SQLModel, table=True):
    """Acceso temporal para que un amigo pruebe la app."""

    id: str = Field(primary_key=True)
    label: str
    token_hash: str = Field(index=True, unique=True)
    created_at: datetime = Field(default_factory=utcnow)
    expires_at: datetime
    revoked: bool = False
    last_used_at: datetime | None = None
