from __future__ import annotations

from pathlib import Path

import docx

from integrations.file_parser.base import BaseFileParser, ParsedDocument


class DocxParser(BaseFileParser):
    def can_parse(self, file_path: Path) -> bool:
        return file_path.suffix.lower() in (".docx", ".doc")

    def parse(self, file_path: Path) -> ParsedDocument:
        doc = docx.Document(str(file_path))
        parts = []

        # Read paragraphs
        for p in doc.paragraphs:
            text = p.text.strip()
            if text:
                parts.append(text)

        # Read tables
        for table in doc.tables:
            table_lines = []
            for row in table.rows:
                cells = [cell.text.strip() for cell in row.cells]
                table_lines.append(" | ".join(cells))
            if table_lines:
                parts.append("\n".join(table_lines))

        full_text = "\n\n".join(parts)
        return ParsedDocument(
            text=full_text,
            page_count=1,
            metadata={"source_file": file_path.name, "size_bytes": file_path.stat().st_size},
        )
