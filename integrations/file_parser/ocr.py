from __future__ import annotations

import logging
from pathlib import Path

import pymupdf

logger = logging.getLogger(__name__)


def perform_ocr_if_needed(file_path: Path, dpi: int = 200) -> tuple[str, bool]:
    """
    Renders PDF pages to images and runs Tesseract OCR if pytesseract and tesseract are available.
    """
    try:
        import pytesseract
        from PIL import Image

        doc = pymupdf.open(str(file_path))
        ocr_pages = []

        for page in doc:
            zoom = dpi / 72.0
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            text = pytesseract.image_to_string(img)
            ocr_pages.append(text)

        doc.close()
        full_text = "\n\n".join(ocr_pages).strip()
        return full_text, True
    except Exception as exc:
        logger.info("OCR not available or failed (%s); continuing with raw text.", exc)
        return "", False
