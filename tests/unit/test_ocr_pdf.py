import sys
import types
from pathlib import Path

import pymupdf
import pytest
from PIL import Image

import integrations.file_parser.ocr as ocr_module
from integrations.file_parser import parse_file
from integrations.file_parser.pdf import PdfPasswordProtectedError, PdfReadError

LONG_TEXT = "Native text page with plenty of extractable characters. " * 3


class _FakeDoc:
    def __init__(self, pages: list, needs_pass: int = 0):
        self._pages = pages
        self.needs_pass = needs_pass
        self.closed = False

    def __iter__(self):
        return iter(self._pages)

    def __len__(self):
        return len(self._pages)

    def __getitem__(self, index):
        return self._pages[index]

    @property
    def page_count(self):
        return len(self._pages)

    def close(self):
        self.closed = True


class _FakePage:
    def __init__(self, text: str):
        self._text = text

    def get_text(self) -> str:
        return self._text


def _install_fake_tesseract(monkeypatch, image_to_string, version_error: Exception | None = None):
    fake = types.ModuleType("pytesseract")
    if version_error is None:
        fake.get_tesseract_version = lambda: "5.3.0"
    else:
        def _raise():
            raise version_error

        fake.get_tesseract_version = _raise
    fake.image_to_string = image_to_string
    monkeypatch.setitem(sys.modules, "pytesseract", fake)
    return fake


def _write_text_pdf(path: Path, text: str = LONG_TEXT) -> Path:
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    doc.save(path)
    doc.close()
    return path


def _write_image_only_pdf(path: Path, png_path: Path, pages: int = 1) -> Path:
    doc = pymupdf.open()
    for _ in range(pages):
        page = doc.new_page()
        page.insert_image(pymupdf.Rect(0, 0, 300, 100), filename=str(png_path))
    doc.save(path)
    doc.close()
    return path


def _png(tmp_path: Path) -> Path:
    png = tmp_path / "page.png"
    Image.new("RGB", (300, 100), "white").save(png)
    return png


def test_ocr_module_imports():
    import importlib

    module = importlib.import_module("integrations.file_parser.ocr")

    assert callable(module.perform_ocr_if_needed)
    assert callable(module.ocr_pdf_pages)
    assert isinstance(module.is_ocr_available(), bool)


def test_pdf_page_is_rendered_to_rgb_image(tmp_path, monkeypatch):
    pdf = _write_text_pdf(tmp_path / "doc.pdf")
    captured = []

    def fake_image_to_string(image):
        captured.append(image)
        return "ocr text"

    _install_fake_tesseract(monkeypatch, fake_image_to_string)

    texts = ocr_module.ocr_pdf_pages(pdf, page_numbers=[0], dpi=72)

    assert texts == ["ocr text"]
    assert len(captured) == 1
    assert isinstance(captured[0], Image.Image)
    assert captured[0].mode == "RGB"
    # The default A4 page (595x842 pt) rendered at 72 dpi keeps 1:1 pixel dimensions.
    assert (captured[0].width, captured[0].height) == (595, 842)


def test_text_pdf_uses_native_extraction_without_ocr(tmp_path, monkeypatch):
    pdf = _write_text_pdf(tmp_path / "text.pdf")

    def boom(*args, **kwargs):
        raise AssertionError("OCR must not run for text-based PDFs")

    monkeypatch.setattr("integrations.file_parser.pdf.ocr_pdf_pages", boom)

    parsed = parse_file(pdf)

    assert "extractable characters" in parsed.text
    assert parsed.is_scanned is False
    assert "ocr_status" not in parsed.metadata


def test_scanned_pdf_uses_ocr_fallback(tmp_path, monkeypatch):
    pdf = _write_image_only_pdf(tmp_path / "scan.pdf", _png(tmp_path))
    _install_fake_tesseract(
        monkeypatch, lambda image: "Recovered OCR text from a scanned page"
    )

    parsed = parse_file(pdf)

    assert parsed.text == "Recovered OCR text from a scanned page"
    assert parsed.is_scanned is True
    assert parsed.metadata["ocr_status"] == "applied"


def test_mixed_pdf_keeps_native_text_and_ocrs_only_empty_pages(tmp_path, monkeypatch):
    png = _png(tmp_path)
    doc = pymupdf.open()
    doc.new_page().insert_text((72, 72), LONG_TEXT)
    doc.new_page().insert_image(pymupdf.Rect(0, 0, 300, 100), filename=str(png))
    pdf = tmp_path / "mixed.pdf"
    doc.save(pdf)
    doc.close()

    rendered = []

    def fake_image_to_string(image):
        rendered.append(image)
        return "OCR recovered page two"

    _install_fake_tesseract(monkeypatch, fake_image_to_string)

    parsed = parse_file(pdf)

    assert "extractable characters" in parsed.text
    assert "OCR recovered page two" in parsed.text
    assert parsed.text.index("extractable characters") < parsed.text.index(
        "OCR recovered page two"
    )
    assert len(rendered) == 1
    assert parsed.is_scanned is False


def test_missing_tesseract_reports_structured_failure(tmp_path, monkeypatch):
    pdf = _write_image_only_pdf(tmp_path / "scan.pdf", _png(tmp_path))
    called = []
    _install_fake_tesseract(
        monkeypatch,
        lambda image: called.append(image) or "should not run",
        version_error=OSError("tesseract is not installed"),
    )

    parsed = parse_file(pdf)

    assert parsed.text == ""
    assert parsed.metadata["ocr_status"] == "unavailable"
    assert "Tesseract" in parsed.metadata["ocr_error"]
    assert called == []


@pytest.mark.parametrize(
    "content",
    [b"", b"%PDF-1.4\nthis is not really a pdf\n"],
    ids=["empty-file", "corrupt-file"],
)
def test_unreadable_pdf_raises_clear_error(tmp_path, content):
    pdf = tmp_path / "broken.pdf"
    pdf.write_bytes(content)

    with pytest.raises(PdfReadError) as exc_info:
        parse_file(pdf)

    assert "not a valid PDF" in str(exc_info.value)


def test_password_protected_pdf_raises_clear_error(tmp_path):
    doc = pymupdf.open()
    doc.new_page().insert_text((72, 72), "secret")
    pdf = tmp_path / "protected.pdf"
    doc.save(
        pdf,
        encryption=pymupdf.PDF_ENCRYPT_AES_256,
        owner_pw="owner",
        user_pw="user",
    )
    doc.close()

    with pytest.raises(PdfPasswordProtectedError) as exc_info:
        parse_file(pdf)

    assert "password-protected" in str(exc_info.value)


def test_ocr_failure_on_one_page_keeps_other_pages(tmp_path, monkeypatch):
    pdf = _write_image_only_pdf(tmp_path / "scan.pdf", _png(tmp_path), pages=2)
    calls = []

    def flaky_image_to_string(image):
        calls.append(image)
        if len(calls) == 1:
            raise RuntimeError("tesseract crashed")
        return "Text from page two"

    _install_fake_tesseract(monkeypatch, flaky_image_to_string)

    parsed = parse_file(pdf)

    assert parsed.text == "Text from page two"
    assert parsed.metadata["ocr_status"] == "applied"
    assert len(calls) == 2


def test_pdf_document_is_closed_after_extraction(tmp_path, monkeypatch):
    pdf = tmp_path / "fake.pdf"
    pdf.write_bytes(b"placeholder")
    doc = _FakeDoc([_FakePage("text " * 20)])
    monkeypatch.setattr("integrations.file_parser.pdf.pymupdf.open", lambda _path: doc)

    parsed = parse_file(pdf)

    assert doc.closed is True
    assert parsed.text == ("text " * 20).strip()


def test_pdf_document_is_closed_when_extraction_fails(tmp_path, monkeypatch):
    pdf = tmp_path / "fake.pdf"
    pdf.write_bytes(b"placeholder")

    class _ExplodingDoc(_FakeDoc):
        def __iter__(self):
            raise RuntimeError("damaged page tree")

    doc = _ExplodingDoc([])
    monkeypatch.setattr("integrations.file_parser.pdf.pymupdf.open", lambda _path: doc)

    with pytest.raises(RuntimeError):
        parse_file(pdf)

    assert doc.closed is True


def test_ocr_document_is_closed_on_unexpected_error(tmp_path, monkeypatch):
    _install_fake_tesseract(monkeypatch, lambda image: "text")

    class _BrokenDoc(_FakeDoc):
        @property
        def page_count(self):
            raise RuntimeError("broken document")

    doc = _BrokenDoc([])
    monkeypatch.setattr("integrations.file_parser.ocr.pymupdf.open", lambda _path: doc)

    with pytest.raises(RuntimeError):
        ocr_module.ocr_pdf_pages(tmp_path / "x.pdf")

    assert doc.closed is True
