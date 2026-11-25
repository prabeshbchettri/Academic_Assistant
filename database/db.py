from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine

from app.settings import settings

logger = logging.getLogger(__name__)

_ENGINE = None
_DEFAULT_INITIALIZED = False


def get_db_path() -> Path:
    db_file = settings.storage_dir / "academic_ai.db"
    db_file.parent.mkdir(parents=True, exist_ok=True)
    return db_file


def get_engine(db_path: Path | None = None):
    global _ENGINE
    if _ENGINE is not None and db_path is None:
        return _ENGINE

    path = db_path or get_db_path()
    database_url = f"sqlite:///{path}"
    engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False},
        echo=False,
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    if db_path is None:
        _ENGINE = engine
    return engine


def init_db(db_path: Path | None = None) -> None:
    global _DEFAULT_INITIALIZED
    from database.migrations import run_migrations

    engine = get_engine(db_path)
    SQLModel.metadata.create_all(engine)
    run_migrations(engine)
    if db_path is None:
        _DEFAULT_INITIALIZED = True
    logger.info("Database initialized at %s", db_path or get_db_path())


def get_session(engine=None) -> Session:
    if engine is None:
        if not _DEFAULT_INITIALIZED:
            init_db()
        return Session(get_engine())
    return Session(engine)
