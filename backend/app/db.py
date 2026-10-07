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


# Columnas agregadas después de crear la base; las descargas viejas quedan como del admin
_NEW_COLUMNS = {
    "job": {
        "owner": "VARCHAR NOT NULL DEFAULT 'admin'",
        "device": "VARCHAR",
    },
    "invite": {
        "token_enc": "VARCHAR",
        "deleted": "BOOLEAN NOT NULL DEFAULT 0",
    },
}


def _add_missing_columns(engine: Engine) -> None:
    inspector = inspect(engine)
    with engine.begin() as conn:
        for table, wanted in _NEW_COLUMNS.items():
            existing = {c["name"] for c in inspector.get_columns(table)}
            for name, ddl in wanted.items():
                if name not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_job_owner ON job (owner)"))
