from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pymupdf

logger = logging.getLogger(__name__)


class OcrUnavailableError(RuntimeError):
    """Raised when pytesseract or the Tesseract executable is unavailable."""


def _load_ocr_dependencies() -> tuple[Any, Any]:
    """
    Imports pytesseract and Pillow and verifies the Tesseract executable is reachable.
    Raises OcrUnavailableError with an actionable message when OCR cannot run.
    """
    try:
        import pytesseract
        from PIL import Image
    except ImportError as exc:
        raise OcrUnavailableError(
            "OCR support requires the 'pytesseract' and 'pillow' packages."
        ) from exc

    try:
        pytesseract.get_tesseract_version()
    except Exception as exc:
        raise OcrUnavailableError(
            "Tesseract OCR is not installed or not on PATH. Install Tesseract "
            "(Windows: https://github.com/UB-Mannheim/tesseract/wiki) or set "
            "pytesseract.pytesseract.tesseract_cmd to the executable."
        ) from exc

    return pytesseract, Image


def is_ocr_available() -> bool:
    """Returns True when pytesseract and the Tesseract executable are usable."""
    try:
        _load_ocr_dependencies()
    except OcrUnavailableError:
        return False
    return True


def _render_page_image(page: Any, image_module: Any, dpi: int) -> Any:
    # Render the page at the requested resolution and release the pixmap right away.
    zoom = dpi / 72.0
    matrix = pymupdf.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=matrix)
    try:
        return image_module.frombytes("RGB", (pix.width, pix.height), pix.samples)
    finally:
        del pix


def ocr_pdf_pages(
    file_path: Path,
    page_numbers: list[int] | None = None,
    dpi: int = 200,
) -> list[str]:
    """
    Renders selected PDF pages to images and runs Tesseract on them.

    Returns one string per requested page, in request order. All pages are processed
    when page_numbers is None. Raises OcrUnavailableError when Tesseract is missing;
    a failure on a single page is logged and yields an empty string for that page.
    """
    pytesseract, image_module = _load_ocr_dependencies()

    doc = pymupdf.open(str(file_path))
    try:
        indices = list(range(doc.page_count)) if page_numbers is None else list(page_numbers)
        results = []
        for index in indices:
            try:
                image = _render_page_image(doc[index], image_module, dpi)
                results.append(pytesseract.image_to_string(image).strip())
            except Exception as exc:
                logger.warning(
                    "OCR failed on page %d of %s: %s", index + 1, file_path.name, exc
                )
                results.append("")
        return results
    finally:
        doc.close()


def perform_ocr_if_needed(file_path: Path, dpi: int = 200) -> tuple[str, bool]:
    """
    OCRs every page of a PDF and returns (text, success).

    Kept for callers that want whole-document OCR; PdfParser uses ocr_pdf_pages so it
    can OCR only the pages that lack a text layer.
    """
    try:
        page_texts = ocr_pdf_pages(file_path, dpi=dpi)
    except OcrUnavailableError as exc:
        logger.warning("%s", exc)
        return "", False

    full_text = "\n\n".join(text for text in page_texts if text).strip()
    return full_text, bool(full_text)
