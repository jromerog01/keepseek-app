from pathlib import Path

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlmodel import SQLModel, create_engine

from app import models  # noqa: F401  (registra las tablas)


def make_engine(db_path: Path) -> Engine:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    SQLModel.metadata.create_all(engine)
    _add_missing_columns(engine)
    return engine


def _add_missing_columns(engine: Engine) -> None:
    """Bases creadas antes de que existiera `job.owner`: sus descargas son del admin."""
    columns = {c["name"] for c in inspect(engine).get_columns("job")}
    if "owner" not in columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE job ADD COLUMN owner VARCHAR NOT NULL DEFAULT 'admin'"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_job_owner ON job (owner)"))
