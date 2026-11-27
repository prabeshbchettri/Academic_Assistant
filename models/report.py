from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


class ReferenceProvenance(str, Enum):
    """Where a bibliography entry came from. Only supplied references are rendered."""

    USER_PROVIDED = "user_provided"
    DOCUMENT_EXTRACTED = "document_extracted"
    RETRIEVAL = "retrieval"
    LLM_SUGGESTION = "llm_suggestion"
    UNVERIFIED = "unverified"


class Citation(BaseModel):
    key: str
    authors: str
    title: str
    year: str
    venue: str = ""
    url: str = ""
    doi: str = ""
    source: str = ""
    # Unknown origin is the safe default: an LLM-suggested source must be marked explicitly.
    provenance: ReferenceProvenance = ReferenceProvenance.UNVERIFIED


class TableData(BaseModel):
    caption: str
    headers: list[str]
    rows: list[list[str]]


class FigureData(BaseModel):
    caption: str
    image_path: str = ""
    description: str = ""


class FrontPage(BaseModel):
    institution: str = "Institute of Engineering"
    university: str = "Tribhuvan University"
    campus: str = "Pulchowk Campus"
    department: str = "Department of Electronics & Computer Engineering"
    document_type: str = "Academic Assignment"
    title: str = ""
    subtitle: str = ""
    course: str = ""
    submitted_by: str = ""
    roll_number: str = ""
    group: str = ""
    program: str = ""
    semester: str = ""
    section: str = ""
    submitted_to: str = ""
    date: str = ""
    logo_path: str = str(
        Path(__file__).resolve().parent.parent
        / "document"
        / "assets"
        / "tu_logo.png"
    )


class SectionDraft(BaseModel):
    heading: str
    body_markdown: str
    tables: list[TableData] = Field(default_factory=list)
    figures: list[FigureData] = Field(default_factory=list)
    citations: list[str] = Field(default_factory=list)
    word_count: int = 0
    missing_placeholders: list[str] = Field(default_factory=list)


class ReportContent(BaseModel):
    title: str
    course: str = ""
    author: str = ""
    date: str = ""
    institution: str = ""
    abstract: str = ""
    sections: list[SectionDraft] = Field(default_factory=list)
    references: list[Citation] = Field(default_factory=list)
    appendix: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    front_page: FrontPage | None = None
    document_type: str = "assignment"
    include_toc: bool = True
    created_at: datetime = Field(default_factory=utc_now)

    def total_word_count(self) -> int:
        abstract_words = len(self.abstract.split()) if self.abstract else 0
        return sum(s.word_count for s in self.sections) + abstract_words

    def get_section(self, heading: str) -> SectionDraft | None:
        for sec in self.sections:
            if sec.heading.lower() == heading.lower():
                return sec
        return None
