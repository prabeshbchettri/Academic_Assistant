from __future__ import annotations

from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(UTC)


class AssignmentTable(SQLModel, table=True):
    __tablename__ = "assignments"

    id: int | None = Field(default=None, primary_key=True)
    title: str = Field(index=True)
    source_type: str = Field(default="manual")
    source_id: str | None = Field(default=None, index=True)
    content_hash: str = Field(index=True)
    raw_text: str
    normalized_text: str
    category: str = Field(default="assignment", index=True)
    status: str = Field(default="pending", index=True)  # pending, in_progress, review, approved, failed
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class SourceRecordTable(SQLModel, table=True):
    __tablename__ = "source_records"

    id: int | None = Field(default=None, primary_key=True)
    assignment_id: int | None = Field(default=None, foreign_key="assignments.id", index=True)
    source_type: str
    external_id: str = Field(index=True)
    url: str | None = None
    author: str | None = None
    received_at: datetime = Field(default_factory=utc_now)


class WorkflowRunTable(SQLModel, table=True):
    __tablename__ = "workflow_runs"

    thread_id: str = Field(primary_key=True)
    assignment_id: int = Field(foreign_key="assignments.id", index=True)
    status: str = Field(default="started", index=True)  # started, interrupted, completed, error
    current_node: str = Field(default="start")
    retry_count: int = Field(default=0)
    state_json: str = Field(default="{}")
    error_message: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class GeneratedDocumentTable(SQLModel, table=True):
    __tablename__ = "generated_documents"

    id: int | None = Field(default=None, primary_key=True)
    assignment_id: int = Field(foreign_key="assignments.id", index=True)
    run_id: str | None = Field(default=None, index=True)
    version: int = Field(default=1)
    docx_path: str
    pdf_path: str | None = None
    engine: str = Field(default="tectonic")
    created_at: datetime = Field(default_factory=utc_now)


class ReferenceDocumentTable(SQLModel, table=True):
    __tablename__ = "reference_documents"

    id: int | None = Field(default=None, primary_key=True)
    course_id: str = Field(index=True)
    filename: str
    path: str
    chunk_count: int = Field(default=0)
    indexed_at: datetime = Field(default_factory=utc_now)


class AuditLogTable(SQLModel, table=True):
    __tablename__ = "audit_logs"

    id: int | None = Field(default=None, primary_key=True)
    assignment_id: int | None = Field(default=None, foreign_key="assignments.id", index=True)
    event: str = Field(index=True)
    detail_json: str = Field(default="{}")
    created_at: datetime = Field(default_factory=utc_now)


class SchemaVersionTable(SQLModel, table=True):
    __tablename__ = "schema_versions"

    version: int = Field(primary_key=True)
    applied_at: datetime = Field(default_factory=utc_now)
