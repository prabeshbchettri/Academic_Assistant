from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class ParsedDocument:
    def __init__(
        self,
        text: str,
        page_count: int = 1,
        metadata: dict | None = None,
        is_scanned: bool = False,
    ):
        self.text = text
        self.page_count = page_count
        self.metadata = metadata or {}
        self.is_scanned = is_scanned


class BaseFileParser(ABC):
    @abstractmethod
    def can_parse(self, file_path: Path) -> bool:
        pass

    @abstractmethod
    def parse(self, file_path: Path) -> ParsedDocument:
        pass
