from __future__ import annotations

import logging
from pathlib import Path

import docx
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls
from docx.shared import Inches, Pt, RGBColor

from app.settings import settings
from configs.schema import CategoryConfig
from document.markdown_to_docx import add_markdown_paragraph
from models.report import ReportContent

logger = logging.getLogger(__name__)


class DocxGenerator:
    def __init__(self, template_path: Path | None = None):
        self.template_path = template_path

    def _set_cell_background(self, cell, fill_hex: str):
        shading = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
        cell._tc.get_or_add_tcPr().append(shading)

    def generate(
        self,
        report: ReportContent,
        config: CategoryConfig,
        assignment_id: int = 1,
        version: int = 1,
    ) -> Path:
        out_dir = settings.storage_dir / "outputs" / str(assignment_id) / f"v{version}"
        out_dir.mkdir(parents=True, exist_ok=True)
        docx_path = out_dir / "report.docx"

        doc = docx.Document()

        # Set page margins
        sections = doc.sections
        for section in sections:
            section.top_margin = Inches(config.formatting.margins_inches.top)
            section.bottom_margin = Inches(config.formatting.margins_inches.bottom)
            section.left_margin = Inches(config.formatting.margins_inches.left)
            section.right_margin = Inches(config.formatting.margins_inches.right)

        # Title Page / Header
        title_p = doc.add_paragraph()
        title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        title_run = title_p.add_run(report.title)
        title_run.font.name = config.formatting.font
        title_run.font.size = Pt(22)
        title_run.bold = True
        title_run.font.color.rgb = RGBColor(0x1B, 0x36, 0x5D)  # Academic Navy

        meta_p = doc.add_paragraph()
        meta_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        meta_text = f"Course: {report.course}  |  Date: {report.date or '2026'}"
        meta_run = meta_p.add_run(meta_text)
        meta_run.font.name = config.formatting.font
        meta_run.font.size = Pt(11)
        meta_run.italic = True
        meta_run.font.color.rgb = RGBColor(0x55, 0x55, 0x55)

        doc.add_paragraph()  # Spacing

        # Abstract if present
        if report.abstract:
            abs_heading = doc.add_heading("Abstract", level=2)
            abs_p = doc.add_paragraph()
            abs_run = abs_p.add_run(report.abstract)
            abs_run.font.name = config.formatting.font
            abs_run.font.size = Pt(10.5)
            abs_run.italic = True
            doc.add_paragraph()

        # Sections
        for idx, sec in enumerate(report.sections, start=1):
            heading_text = f"{idx}. {sec.heading}" if config.formatting.heading_numbering else sec.heading
            h = doc.add_heading(heading_text, level=1)
            h.paragraph_format.space_before = Pt(14)
            h.paragraph_format.space_after = Pt(6)

            # Add body with markdown conversion
            add_markdown_paragraph(doc, sec.body_markdown)

            # Add tables if present
            for table_data in sec.tables:
                caption_p = doc.add_paragraph(f"Table: {table_data.caption}")
                caption_p.runs[0].font.italic = True
                caption_p.runs[0].font.size = Pt(10)

                cols = len(table_data.headers)
                t = doc.add_table(rows=1 + len(table_data.rows), cols=cols)
                t.alignment = WD_TABLE_ALIGNMENT.CENTER

                # Headers
                for c_idx, h_text in enumerate(table_data.headers):
                    cell = t.cell(0, c_idx)
                    cell.text = h_text
                    cell.paragraphs[0].runs[0].bold = True
                    self._set_cell_background(cell, "EAEAEA")

                # Rows
                for r_idx, row in enumerate(table_data.rows, start=1):
                    for c_idx, val in enumerate(row):
                        cell = t.cell(r_idx, c_idx)
                        cell.text = str(val)

                doc.add_paragraph()  # Spacing after table

        # References
        if report.references:
            doc.add_heading("References", level=1)
            for ref in report.references:
                ref_p = doc.add_paragraph()
                ref_run = ref_p.add_run(f"{ref.key} {ref.authors}, \"{ref.title}\", {ref.venue}, {ref.year}.")
                ref_run.font.size = Pt(10)

        doc.save(str(docx_path))
        logger.info("Saved DOCX document at %s", docx_path)
        return docx_path
