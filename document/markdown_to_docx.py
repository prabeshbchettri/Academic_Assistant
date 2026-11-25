from __future__ import annotations

import re

from docx.document import Document as DocxDocument
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Inches, Pt, RGBColor

_MISSING_RE = re.compile(r"\[\[MISSING:\s*([^\]]+)\]\]")
_TABLE_SEPARATOR_RE = re.compile(r"^:?-{3,}:?$")


def _shade_cell(cell, fill_hex: str) -> None:
    shading = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    cell._tc.get_or_add_tcPr().append(shading)


def _split_row(line: str) -> list[str]:
    row = line.strip()
    if row.startswith("|"):
        row = row[1:]
    if row.endswith("|"):
        row = row[:-1]
    return [cell.strip() for cell in row.split("|")]


def _is_table_separator(line: str) -> bool:
    cells = _split_row(line)
    return bool(cells) and all(_TABLE_SEPARATOR_RE.match(cell) for cell in cells)


def _repeat_header(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    header = OxmlElement("w:tblHeader")
    header.set(qn("w:val"), "true")
    tr_pr.append(header)


def add_markdown_table(
    doc: DocxDocument,
    header_line: str,
    row_lines: list[str],
    font_name: str = "Times New Roman",
) -> None:
    header = _split_row(header_line)
    rows = [_split_row(line) for line in row_lines]
    column_count = max([len(header), *(len(row) for row in rows)])

    def padded(cells: list[str]) -> list[str]:
        return (cells + [""] * column_count)[:column_count]

    table = doc.add_table(rows=1 + len(rows), cols=column_count)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = True

    for column, text in enumerate(padded(header)):
        cell = table.cell(0, column)
        cell.text = ""
        paragraph = cell.paragraphs[0]
        paragraph.paragraph_format.space_after = Pt(1)
        run = paragraph.add_run(text)
        run.bold = True
        run.font.name = font_name
        run.font.size = Pt(9.5)
        _shade_cell(cell, "E8EEF5")

    for row_index, row in enumerate(rows, start=1):
        for column, text in enumerate(padded(row)):
            cell = table.cell(row_index, column)
            cell.text = ""
            paragraph = cell.paragraphs[0]
            paragraph.paragraph_format.space_after = Pt(1)
            run = paragraph.add_run(text)
            run.font.name = font_name
            run.font.size = Pt(9.5)

    _repeat_header(table.rows[0])
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def add_markdown_paragraph(
    doc: DocxDocument,
    text: str,
    font_name: str = "Times New Roman",
) -> None:
    lines = text.strip().split("\n")
    in_code_block = False
    code_lines: list[str] = []

    index = 0
    while index < len(lines):
        stripped = lines[index].strip()

        if stripped.startswith("```"):
            if in_code_block:
                paragraph = doc.add_paragraph()
                paragraph.paragraph_format.left_indent = Inches(0.35)
                paragraph.paragraph_format.space_before = Pt(4)
                paragraph.paragraph_format.space_after = Pt(6)
                run = paragraph.add_run("\n".join(code_lines))
                run.font.name = "Courier New"
                run.font.size = Pt(9)
                code_lines.clear()
                in_code_block = False
            else:
                in_code_block = True
            index += 1
            continue

        if in_code_block:
            code_lines.append(lines[index])
            index += 1
            continue

        if not stripped:
            index += 1
            continue

        if (
            stripped.startswith("|")
            and index + 1 < len(lines)
            and _is_table_separator(lines[index + 1].strip())
        ):
            row_lines: list[str] = []
            index += 2
            while index < len(lines) and lines[index].strip().startswith("|"):
                row_lines.append(lines[index].strip())
                index += 1
            add_markdown_table(doc, stripped, row_lines, font_name=font_name)
            continue

        if stripped.startswith("#### "):
            doc.add_heading(stripped[5:], level=4)
        elif stripped.startswith("### "):
            doc.add_heading(stripped[4:], level=3)
        elif stripped.startswith("## "):
            doc.add_heading(stripped[3:], level=2)
        elif stripped.startswith("# "):
            doc.add_heading(stripped[2:], level=1)
        elif stripped.startswith(("- ", "* ", "+ ")):
            paragraph = doc.add_paragraph(style="List Bullet")
            paragraph.paragraph_format.space_after = Pt(3)
            format_inline_markdown(paragraph, stripped[2:], font_name=font_name)
        elif re.match(r"^\d+\.\s+", stripped):
            content = re.sub(r"^\d+\.\s+", "", stripped)
            paragraph = doc.add_paragraph(style="List Number")
            paragraph.paragraph_format.space_after = Pt(3)
            format_inline_markdown(paragraph, content, font_name=font_name)
        elif stripped.startswith(">"):
            paragraph = doc.add_paragraph()
            paragraph.paragraph_format.left_indent = Inches(0.35)
            paragraph.paragraph_format.space_before = Pt(4)
            paragraph.paragraph_format.space_after = Pt(6)
            format_inline_markdown(
                paragraph, stripped.lstrip("> ").strip(), font_name=font_name
            )
            for run in paragraph.runs:
                run.italic = True
                run.font.color.rgb = RGBColor(0x47, 0x55, 0x69)
        elif re.fullmatch(r"(-{3,}|\*{3,}|_{3,})", stripped):
            paragraph = doc.add_paragraph()
            p_pr = paragraph._p.get_or_add_pPr()
            borders = OxmlElement("w:pBdr")
            bottom = OxmlElement("w:bottom")
            bottom.set(qn("w:val"), "single")
            bottom.set(qn("w:sz"), "6")
            bottom.set(qn("w:space"), "1")
            bottom.set(qn("w:color"), "BCCCDC")
            borders.append(bottom)
            p_pr.append(borders)
        else:
            paragraph = doc.add_paragraph()
            paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            paragraph.paragraph_format.space_after = Pt(6)
            format_inline_markdown(paragraph, stripped, font_name=font_name)

        index += 1


def format_inline_markdown(
    paragraph,
    text: str,
    font_name: str = "Times New Roman",
) -> None:
    text = _MISSING_RE.sub(
        lambda match: f"[To be completed: {match.group(1).strip()}]",
        text,
    )
    tokens = re.split(r"(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)", text)
    for token in tokens:
        if not token:
            continue
        if token.startswith("**") and token.endswith("**"):
            run = paragraph.add_run(token[2:-2])
            run.bold = True
            run.font.name = font_name
        elif token.startswith("*") and token.endswith("*"):
            run = paragraph.add_run(token[1:-1])
            run.italic = True
            run.font.name = font_name
        elif token.startswith("`") and token.endswith("`"):
            run = paragraph.add_run(token[1:-1])
            run.font.name = "Courier New"
            run.font.size = Pt(9.5)
        else:
            run = paragraph.add_run(token)
            run.font.name = font_name
