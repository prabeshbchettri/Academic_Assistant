from __future__ import annotations

from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver

from app.settings import settings


def get_checkpointer(db_path: Path | None = None) -> SqliteSaver:
    target = db_path or (settings.storage_dir / "workflow_checkpoints.db")
    target.parent.mkdir(parents=True, exist_ok=True)
    import sqlite3
    conn = sqlite3.connect(str(target), check_same_thread=False)
    return SqliteSaver(conn)
