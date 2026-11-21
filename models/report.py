from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


class Citation(BaseModel):
    key: str
    authors: str
    title: str
    year: str
    venue: str = ""
    url: str = ""


class TableData(BaseModel):
    caption: str
    headers: list[str]
    rows: list[list[str]]


class FigureData(BaseModel):
    caption: str
    image_path: str = ""
    description: str = ""


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
    created_at: datetime = Field(default_factory=utc_now)

    def total_word_count(self) -> int:
        return sum(s.word_count for s in self.sections) + (len(self.abstract.split()) if self.abstract else 0)

    def get_section(self, heading: str) -> SectionDraft | None:
        for sec in self.sections:
            if sec.heading.lower() == heading.lower():
                return sec
        return None
