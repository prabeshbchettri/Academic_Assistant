from __future__ import annotations

from pathlib import Path

import pymupdf

from integrations.file_parser.base import BaseFileParser, ParsedDocument
from integrations.file_parser.ocr import perform_ocr_if_needed


class PdfParser(BaseFileParser):
    def can_parse(self, file_path: Path) -> bool:
        return file_path.suffix.lower() == ".pdf"

    def parse(self, file_path: Path) -> ParsedDocument:
        doc = pymupdf.open(str(file_path))
        text_parts = []
        page_count = len(doc)
        total_chars = 0

        for page in doc:  # type: ignore[attr-defined]
            page_text = page.get_text()
            text_parts.append(page_text)
            total_chars += len(page_text.strip())

        extracted_text = "\n\n".join(text_parts).strip()
        doc.close()

        # If very little text is extracted relative to page count, it's likely scanned
        is_scanned = (total_chars / max(1, page_count)) < 40

        if is_scanned:
            ocr_text, ocr_success = perform_ocr_if_needed(file_path)
            if ocr_success and len(ocr_text) > len(extracted_text):
                extracted_text = ocr_text

        return ParsedDocument(
            text=extracted_text,
            page_count=page_count,
            metadata={"source_file": file_path.name, "size_bytes": file_path.stat().st_size},
            is_scanned=is_scanned,
        )
