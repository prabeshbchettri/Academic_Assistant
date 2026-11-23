from __future__ import annotations

import logging

from sqlmodel import Session, select

from database.models import SchemaVersionTable, utc_now

logger = logging.getLogger(__name__)

CURRENT_SCHEMA_VERSION = 1


def run_migrations(engine) -> None:
    with Session(engine) as session:
        statement = select(SchemaVersionTable).order_by(SchemaVersionTable.version.desc())  # type: ignore
        latest = session.exec(statement).first()

        if latest is None:
            # Fresh database, initialize schema version
            schema_ver = SchemaVersionTable(version=CURRENT_SCHEMA_VERSION, applied_at=utc_now())
            session.add(schema_ver)
            session.commit()
            logger.info("Recorded base schema version %d", CURRENT_SCHEMA_VERSION)
        elif latest.version < CURRENT_SCHEMA_VERSION:
            # Future schema migration steps can be added here sequentially
            logger.info("Migrated schema from %d to %d", latest.version, CURRENT_SCHEMA_VERSION)
            latest.version = CURRENT_SCHEMA_VERSION
            session.add(latest)
            session.commit()
