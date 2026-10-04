from pathlib import Path

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
    return engine
