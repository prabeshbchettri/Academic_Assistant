import tempfile
from pathlib import Path

import docx

from integrations.file_parser import parse_file
from integrations.normalizer import normalize_input
from models.assignment import RawInput, SourceType


def test_text_parser():
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", encoding="utf-8", delete=False) as f:
        f.write("Line 1\nLine 2\nLine 3")
        temp_path = Path(f.name)

    try:
        parsed = parse_file(temp_path)
        assert "Line 1" in parsed.text
        assert "Line 3" in parsed.text
    finally:
        temp_path.unlink()


def test_docx_parser():
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
        doc = docx.Document()
        doc.add_paragraph("First paragraph in DOCX.")
        doc.add_paragraph("Second paragraph in DOCX.")
        doc.save(f.name)
        temp_path = Path(f.name)

    try:
        parsed = parse_file(temp_path)
        assert "First paragraph in DOCX." in parsed.text
    finally:
        temp_path.unlink()


def test_normalizer_and_deduplication():
    raw1 = RawInput(
        source_type=SourceType.MANUAL,
        title="",
        raw_text="Title: Circuit Analysis\n\nMeasure voltage.",
    )
    norm1 = normalize_input(raw1)
    assert norm1.title == "Circuit Analysis"
    assert norm1.content_hash != ""

    raw2 = RawInput(
        source_type=SourceType.MANUAL,
        title="",
        raw_text="  Title: Circuit Analysis \n\n  Measure voltage.  ",
    )
    norm2 = normalize_input(raw2)
    # Deduplication hash must match despite whitespace variation
    assert norm1.content_hash == norm2.content_hash
