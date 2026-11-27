from __future__ import annotations

import logging
from pathlib import Path

import pymupdf

from integrations.file_parser.base import BaseFileParser, ParsedDocument
from integrations.file_parser.ocr import OcrUnavailableError, ocr_pdf_pages

logger = logging.getLogger(__name__)

# Pages with less extractable text than this are treated as scanned and sent to OCR.
MIN_TEXT_CHARS_PER_PAGE = 40


class PdfReadError(ValueError):
    """Raised when a PDF cannot be opened (empty, corrupt, or not a PDF)."""


class PdfPasswordProtectedError(ValueError):
    """Raised when a PDF is encrypted and requires a password to open."""


class PdfParser(BaseFileParser):
    def can_parse(self, file_path: Path) -> bool:
        return file_path.suffix.lower() == ".pdf"

    def parse(self, file_path: Path) -> ParsedDocument:
        try:
            doc = pymupdf.open(str(file_path))
        except pymupdf.FileDataError as exc:
            raise PdfReadError(
                f"Could not read '{file_path.name}': the file is empty, corrupt, "
                "or not a valid PDF."
            ) from exc

        if doc.needs_pass:
            doc.close()
            raise PdfPasswordProtectedError(
                f"'{file_path.name}' is password-protected. Remove the password "
                "before uploading it."
            )

        try:
            page_texts = []
            for page in doc:
                try:
                    page_texts.append(page.get_text())
                except Exception as exc:
                    logger.warning(
                        "Could not extract text from page %d of %s: %s",
                        len(page_texts) + 1,
                        file_path.name,
                        exc,
                    )
                    page_texts.append("")
            page_count = len(doc)
        finally:
            doc.close()

        metadata = {
            "source_file": file_path.name,
            "size_bytes": file_path.stat().st_size,
        }

        # OCR only the pages without a usable text layer, preserving extractable text.
        sparse_pages = [
            index
            for index, text in enumerate(page_texts)
            if len(text.strip()) < MIN_TEXT_CHARS_PER_PAGE
        ]
        is_scanned = bool(page_texts) and len(sparse_pages) == page_count

        if sparse_pages:
            merged_texts = list(page_texts)
            try:
                ocr_texts = ocr_pdf_pages(file_path, page_numbers=sparse_pages)
            except OcrUnavailableError as exc:
                logger.warning(
                    "No OCR available for %s; scanned pages will have no text. %s",
                    file_path.name,
                    exc,
                )
                metadata["ocr_status"] = "unavailable"
                metadata["ocr_error"] = str(exc)
            except Exception as exc:
                logger.warning("OCR failed for %s: %s", file_path.name, exc)
                metadata["ocr_status"] = "failed"
                metadata["ocr_error"] = str(exc)
            else:
                applied = False
                for index, ocr_text in zip(sparse_pages, ocr_texts, strict=True):
                    if len(ocr_text) > len(merged_texts[index].strip()):
                        merged_texts[index] = ocr_text
                        applied = True
                metadata["ocr_status"] = "applied" if applied else "no_text"
            page_texts = merged_texts

        extracted_text = "\n\n".join(page_texts).strip()

        return ParsedDocument(
            text=extracted_text,
            page_count=page_count,
            metadata=metadata,
            is_scanned=is_scanned,
        )
