from __future__ import annotations

import logging
from pathlib import Path

import docx
from docx.document import Document as DocxDocument
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Inches, Pt, RGBColor

from app.settings import settings
from configs.schema import CategoryConfig
from document.markdown_to_docx import add_markdown_paragraph
from models.report import FrontPage, ReportContent, TableData

logger = logging.getLogger(__name__)

NAVY = RGBColor(0x1B, 0x36, 0x5D)
MUTED = RGBColor(0x62, 0x7D, 0x98)


class DocxGenerator:
    def __init__(self, template_path: Path | None = None):
        self.template_path = template_path

    def _set_cell_background(self, cell, fill_hex: str) -> None:
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
        section = doc.sections[0]
        section.top_margin = Inches(config.formatting.margins_inches.top)
        section.bottom_margin = Inches(config.formatting.margins_inches.bottom)
        section.left_margin = Inches(config.formatting.margins_inches.left)
        section.right_margin = Inches(config.formatting.margins_inches.right)
        section.different_first_page_header_footer = True

        self._configure_styles(doc, config)
        self._add_header_footer(section, report, config)
        self._enable_field_updates(doc)
        doc.core_properties.title = report.title
        author = report.author
        if not author and report.front_page:
            author = report.front_page.submitted_by
        doc.core_properties.author = author

        if report.front_page:
            self._add_front_page(doc, report.front_page, config)
            doc.add_page_break()
        else:
            title_p = doc.add_paragraph()
            title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            title_run = title_p.add_run(report.title)
            self._style_run(title_run, config, size=22, bold=True, color=NAVY)

            meta_p = doc.add_paragraph()
            meta_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            meta_run = meta_p.add_run(
                f"Course: {report.course}  |  Date: {report.date or '2026'}"
            )
            self._style_run(meta_run, config, size=11, italic=True, color=MUTED)
            doc.add_paragraph()

        if report.include_toc and report.front_page:
            self._add_toc(doc)
            doc.add_page_break()

        if report.abstract:
            heading = doc.add_heading("Abstract", level=2)
            heading.paragraph_format.space_before = Pt(0)
            abstract_p = doc.add_paragraph()
            abstract_p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            abstract_run = abstract_p.add_run(report.abstract)
            self._style_run(abstract_run, config, size=10.5, italic=True)
            doc.add_paragraph()

        table_number = 1
        for index, sec in enumerate(report.sections, start=1):
            heading_text = (
                f"{index}. {sec.heading}"
                if config.formatting.heading_numbering
                else sec.heading
            )
            heading = doc.add_heading(heading_text, level=1)
            heading.paragraph_format.space_before = Pt(14)
            heading.paragraph_format.space_after = Pt(6)

            add_markdown_paragraph(doc, sec.body_markdown)

            for table_data in sec.tables:
                self._add_data_table(doc, table_data, config, table_number)
                table_number += 1

        if report.references:
            doc.add_page_break()
            doc.add_heading("References", level=1)
            for reference in report.references:
                ref_p = doc.add_paragraph()
                ref_p.paragraph_format.left_indent = Inches(0.3)
                ref_p.paragraph_format.first_line_indent = Inches(-0.3)
                ref_p.paragraph_format.space_after = Pt(4)
                ref_text = (
                    f"{reference.key} {reference.authors}, \"{reference.title}\", "
                    f"{reference.venue}, {reference.year}."
                )
                ref_run = ref_p.add_run(ref_text)
                self._style_run(ref_run, config, size=9.5)

        doc.save(str(docx_path))
        logger.info("Saved DOCX document at %s", docx_path)
        return docx_path

    def _configure_styles(self, doc: DocxDocument, config: CategoryConfig) -> None:
        font_name = config.formatting.font
        normal = doc.styles["Normal"]
        self._set_style_font(normal, font_name)
        normal.font.size = Pt(config.formatting.font_size)
        normal.font.color.rgb = RGBColor(0x1A, 0x1A, 0x1A)
        normal.paragraph_format.line_spacing = config.formatting.line_spacing
        normal.paragraph_format.space_after = Pt(6)
        normal.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

        for style_name, size, before, after in (
            ("Heading 1", 16, 18, 8),
            ("Heading 2", 13, 14, 6),
            ("Heading 3", 11.5, 12, 4),
            ("Heading 4", 11, 10, 4),
        ):
            style = doc.styles[style_name]
            self._set_style_font(style, font_name)
            style.font.size = Pt(size)
            style.font.bold = True
            style.font.color.rgb = NAVY
            style.paragraph_format.space_before = Pt(before)
            style.paragraph_format.space_after = Pt(after)
            style.paragraph_format.keep_with_next = True

        for style_name in ("List Bullet", "List Number"):
            style = doc.styles[style_name]
            self._set_style_font(style, font_name)
            style.font.size = Pt(config.formatting.font_size)
            style.paragraph_format.space_after = Pt(3)

    @staticmethod
    def _set_style_font(style, font_name: str) -> None:
        style.font.name = font_name
        r_pr = style.element.get_or_add_rPr()
        r_fonts = r_pr.get_or_add_rFonts()
        r_fonts.set(qn("w:eastAsia"), font_name)

    def _style_run(
        self,
        run,
        config: CategoryConfig,
        *,
        size: float | None = None,
        bold: bool = False,
        italic: bool = False,
        color: RGBColor | None = None,
    ) -> None:
        run.font.name = config.formatting.font
        if size is not None:
            run.font.size = Pt(size)
        run.bold = bold
        run.italic = italic
        if color is not None:
            run.font.color.rgb = color

    def _add_header_footer(
        self,
        section,
        report: ReportContent,
        config: CategoryConfig,
    ) -> None:
        header = section.header
        header.is_linked_to_previous = False
        header_p = header.paragraphs[0]
        header_p.text = ""
        header_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        header_p.paragraph_format.space_after = Pt(0)
        header_run = header_p.add_run(report.title)
        self._style_run(header_run, config, size=8.5, italic=True, color=MUTED)

        p_pr = header_p._p.get_or_add_pPr()
        borders = OxmlElement("w:pBdr")
        bottom = OxmlElement("w:bottom")
        bottom.set(qn("w:val"), "single")
        bottom.set(qn("w:sz"), "4")
        bottom.set(qn("w:space"), "1")
        bottom.set(qn("w:color"), "D9E2EC")
        borders.append(bottom)
        p_pr.append(borders)

        footer = section.footer
        footer.is_linked_to_previous = False
        footer_p = footer.paragraphs[0]
        footer_p.text = ""
        footer_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        self._add_field(footer_p, "PAGE", "1")
        for run in footer_p.runs:
            self._style_run(run, config, size=8.5, color=MUTED)

        first_footer = section.first_page_footer
        first_footer.is_linked_to_previous = False
        first_footer_p = first_footer.paragraphs[0]
        first_footer_p.text = ""
        first_footer_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        if report.front_page and report.front_page.date:
            date_run = first_footer_p.add_run(report.front_page.date)
            self._style_run(date_run, config, size=11, italic=True)

    def _add_field(self, paragraph, instruction: str, placeholder: str) -> None:
        run = paragraph.add_run()

        begin = OxmlElement("w:fldChar")
        begin.set(qn("w:fldCharType"), "begin")
        begin.set(qn("w:dirty"), "true")

        instruction_element = OxmlElement("w:instrText")
        instruction_element.set(qn("xml:space"), "preserve")
        instruction_element.text = f" {instruction} "

        separate = OxmlElement("w:fldChar")
        separate.set(qn("w:fldCharType"), "separate")

        value = OxmlElement("w:t")
        value.text = placeholder

        end = OxmlElement("w:fldChar")
        end.set(qn("w:fldCharType"), "end")

        run._r.append(begin)
        run._r.append(instruction_element)
        run._r.append(separate)
        run._r.append(value)
        run._r.append(end)

    @staticmethod
    def _enable_field_updates(doc: DocxDocument) -> None:
        settings_element = doc.settings.element
        update_fields = OxmlElement("w:updateFields")
        update_fields.set(qn("w:val"), "true")
        settings_element.append(update_fields)

    def _add_front_page(
        self,
        doc: DocxDocument,
        front_page: FrontPage,
        config: CategoryConfig,
    ) -> None:
        logo = Path(front_page.logo_path) if front_page.logo_path else None
        if logo and logo.exists():
            doc.add_picture(str(logo), width=Inches(1.05))
            doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
            doc.paragraphs[-1].paragraph_format.space_after = Pt(8)

        self._centered_line(doc, front_page.university.upper(), 12, config, bold=True)
        self._centered_line(
            doc,
            front_page.institution,
            19,
            config,
            bold=True,
            color=NAVY,
        )
        self._centered_line(doc, front_page.campus, 12, config)
        if front_page.department:
            self._centered_line(doc, front_page.department, 12, config)

        self._add_rule(doc)

        self._centered_line(
            doc, front_page.document_type.upper(), 11, config, bold=True
        )
        self._centered_line(
            doc,
            front_page.title,
            22,
            config,
            bold=True,
            color=NAVY,
        )
        if front_page.subtitle:
            self._centered_line(
                doc, front_page.subtitle, 12, config, italic=True, color=MUTED
            )
        if front_page.course:
            self._centered_line(
                doc, front_page.course, 11, config, italic=True, color=MUTED
            )

        spacer = doc.add_paragraph()
        spacer.paragraph_format.space_after = Pt(18)

        details = doc.add_table(rows=1, cols=2)
        details.autofit = False
        details.alignment = WD_TABLE_ALIGNMENT.CENTER
        for row in details.rows:
            row.cells[0].width = Inches(3.05)
            row.cells[1].width = Inches(3.05)

        submitted_by = [
            ("Name", front_page.submitted_by),
            ("Roll No.", front_page.roll_number),
            ("Group", front_page.group),
        ]
        self._detail_cell(
            details.cell(0, 0), "Submitted by", submitted_by, config
        )

        submitted_to = front_page.department or front_page.submitted_to
        if submitted_to:
            self._detail_cell(
                details.cell(0, 1),
                "Submitted to",
                [("", submitted_to)],
                config,
            )


    def _detail_cell(
        self,
        cell,
        title: str,
        lines: list[tuple[str, str]],
        config: CategoryConfig,
    ) -> None:
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.TOP
        cell.text = ""

        title_p = cell.paragraphs[0]
        title_p.paragraph_format.space_after = Pt(7)
        title_run = title_p.add_run(title)
        self._style_run(title_run, config, size=11, bold=True)

        for label, value in lines:
            if not value:
                continue
            paragraph = cell.add_paragraph()
            paragraph.paragraph_format.space_after = Pt(2)
            if label:
                label_run = paragraph.add_run(f"{label}: ")
                self._style_run(label_run, config, size=10.5, bold=True)
            value_run = paragraph.add_run(value)
            self._style_run(value_run, config, size=10.5)

    def _centered_line(
        self,
        doc: DocxDocument,
        text: str,
        size: int,
        config: CategoryConfig,
        *,
        bold: bool = False,
        italic: bool = False,
        color: RGBColor | None = None,
    ) -> None:
        paragraph = doc.add_paragraph()
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph.paragraph_format.space_after = Pt(3)
        run = paragraph.add_run(text)
        self._style_run(
            run, config, size=size, bold=bold, italic=italic, color=color
        )

    def _add_rule(self, doc: DocxDocument) -> None:
        paragraph = doc.add_paragraph()
        paragraph.paragraph_format.space_before = Pt(6)
        paragraph.paragraph_format.space_after = Pt(10)
        p_pr = paragraph._p.get_or_add_pPr()
        borders = OxmlElement("w:pBdr")
        bottom = OxmlElement("w:bottom")
        bottom.set(qn("w:val"), "single")
        bottom.set(qn("w:sz"), "8")
        bottom.set(qn("w:space"), "1")
        bottom.set(qn("w:color"), "1B365D")
        borders.append(bottom)
        p_pr.append(borders)

    def _add_toc(self, doc: DocxDocument) -> None:
        heading = doc.add_heading("Table of Contents", level=1)
        heading.alignment = WD_ALIGN_PARAGRAPH.CENTER

        paragraph = doc.add_paragraph()
        paragraph.paragraph_format.space_before = Pt(10)
        self._add_field(
            paragraph,
            'TOC \\o "1-3" \\h \\z \\u',
            "Update this field in Word to build the table of contents.",
        )

    def _add_data_table(
        self,
        doc: DocxDocument,
        table_data: TableData,
        config: CategoryConfig,
        table_number: int,
    ) -> None:
        caption_p = doc.add_paragraph()
        caption_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        caption_p.paragraph_format.space_before = Pt(8)
        caption_p.paragraph_format.space_after = Pt(4)
        caption_run = caption_p.add_run(f"Table {table_number}: {table_data.caption}")
        self._style_run(caption_run, config, size=9.5, italic=True, color=MUTED)

        table = doc.add_table(rows=1 + len(table_data.rows), cols=len(table_data.headers))
        table.style = "Table Grid"
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.autofit = True

        for column, header_text in enumerate(table_data.headers):
            cell = table.cell(0, column)
            cell.text = ""
            paragraph = cell.paragraphs[0]
            paragraph.paragraph_format.space_after = Pt(1)
            run = paragraph.add_run(str(header_text))
            self._style_run(run, config, size=9.5, bold=True)
            self._set_cell_background(cell, "E8EEF5")

        for row_index, row in enumerate(table_data.rows, start=1):
            for column, value in enumerate(row):
                cell = table.cell(row_index, column)
                cell.text = ""
                paragraph = cell.paragraphs[0]
                paragraph.paragraph_format.space_after = Pt(1)
                run = paragraph.add_run(str(value))
                self._style_run(run, config, size=9.5)

        tr_pr = table.rows[0]._tr.get_or_add_trPr()
        header_flag = OxmlElement("w:tblHeader")
        header_flag.set(qn("w:val"), "true")
        tr_pr.append(header_flag)
        doc.add_paragraph().paragraph_format.space_after = Pt(2)
