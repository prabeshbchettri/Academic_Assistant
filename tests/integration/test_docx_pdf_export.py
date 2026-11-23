
from configs.schema import load_category_config
from document.docx_generator import DocxGenerator
from document.pdf_exporter import PdfExporter
from models.report import Citation, ReportContent, SectionDraft


def test_docx_and_pdf_export_pipeline():
    cfg = load_category_config("assignment")
    report = ReportContent(
        title="Integration Test Document",
        course="CS 401",
        author="Tester",
        date="2026",
        abstract="Integration test abstract content.",
        sections=[
            SectionDraft(
                heading="Introduction",
                body_markdown="This is the introduction section discussing algorithms.",
                word_count=7,
            ),
            SectionDraft(
                heading="Conclusion",
                body_markdown="This is the final conclusion of the test.",
                word_count=8,
            ),
        ],
        references=[
            Citation(key="[1]", authors="Knuth", title="Art of Programming", year="1968")
        ],
    )

    docx_gen = DocxGenerator()
    docx_path = docx_gen.generate(report, cfg, assignment_id=999, version=1)
    assert docx_path.exists()

    # Reopen to confirm valid DOCX
    import docx
    opened_doc = docx.Document(str(docx_path))
    assert len(opened_doc.paragraphs) > 0

    # Test PDF Exporter
    pdf_exporter = PdfExporter()
    pdf_path = pdf_exporter.export(report, docx_path, assignment_id=999, version=1)
    if pdf_path:
        assert pdf_path.exists()
