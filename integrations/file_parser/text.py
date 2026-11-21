from __future__ import annotations

from pathlib import Path

from integrations.file_parser.base import BaseFileParser, ParsedDocument


class TextParser(BaseFileParser):
    def can_parse(self, file_path: Path) -> bool:
        return file_path.suffix.lower() in (".txt", ".md", ".markdown", ".csv", ".tsv")

    def parse(self, file_path: Path) -> ParsedDocument:
        raw_bytes = file_path.read_bytes()
        # Try UTF-8 first, then fallback to latin-1
        try:
            text = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            text = raw_bytes.decode("latin-1", errors="replace")

        return ParsedDocument(
            text=text,
            page_count=1,
            metadata={"source_file": file_path.name, "size_bytes": file_path.stat().st_size},
        )
