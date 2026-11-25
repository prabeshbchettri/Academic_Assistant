from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


class Category(StrEnum):
    ASSIGNMENT = "assignment"
    INITIAL_LAB = "initial_lab"
    FINAL_LAB = "final_lab"


class SourceType(StrEnum):
    MANUAL = "manual"
    FILE = "file"
    CLASSROOM = "classroom"
    GMAIL = "gmail"


class RawInput(BaseModel):
    source_type: SourceType = SourceType.MANUAL
    title: str = ""
    raw_text: str = ""
    file_path: str | None = None
    course_name: str | None = None
    due_date: str | None = None
    external_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class NormalizedInput(BaseModel):
    title: str
    cleaned_text: str
    source_type: SourceType
    content_hash: str
    course_name: str | None = None
    due_date: str | None = None
    attachments: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class ClassificationResult(BaseModel):
    category: Category
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str
    method: str = "rule"  # "rule", "llm", or "manual"


class MissingInfoRequest(BaseModel):
    is_missing: bool = False
    questions: list[str] = Field(default_factory=list)
    expected_fields: list[str] = Field(default_factory=list)
    answers: dict[str, str] = Field(default_factory=dict)
