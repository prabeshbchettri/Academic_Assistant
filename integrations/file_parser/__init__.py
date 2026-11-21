from __future__ import annotations

from pathlib import Path

from integrations.file_parser.base import BaseFileParser, ParsedDocument
from integrations.file_parser.docx import DocxParser
from integrations.file_parser.pdf import PdfParser
from integrations.file_parser.text import TextParser

MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB


class UnsupportedFileError(ValueError):
    pass


class FileTooLargeError(ValueError):
    pass


PARSERS: list[BaseFileParser] = [
    PdfParser(),
    DocxParser(),
    TextParser(),
]


def parse_file(file_path: Path | str) -> ParsedDocument:
    path = Path(file_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    if path.stat().st_size > MAX_FILE_SIZE_BYTES:
        raise FileTooLargeError(f"File size exceeds 25 MB limit: {path.name}")

    for parser in PARSERS:
        if parser.can_parse(path):
            return parser.parse(path)

    raise UnsupportedFileError(f"Unsupported file format: {path.suffix}")
