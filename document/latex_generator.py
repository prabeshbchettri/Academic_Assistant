from __future__ import annotations

import re
from pathlib import Path

from jinja2 import Environment

from document.latex_escape import escape_latex
from models.report import ReportContent

_MISSING_RE = re.compile(r"\[\[MISSING:\s*([^\]]+)\]\]")
_TABLE_SEPARATOR_RE = re.compile(r"^:?-{3,}:?$")


def _prepare_text(text: str) -> str:
    return _MISSING_RE.sub(
        lambda match: f"[To be completed: {match.group(1).strip()}]",
        text,
    )


def _inline(text: str) -> str:
    """Escape text and convert the supported inline Markdown to LaTeX."""
    text = _prepare_text(text)
    parts = re.split(r"(`[^`]+`)", text)
    rendered: list[str] = []
    for part in parts:
        if part.startswith("`") and part.endswith("`") and len(part) >= 2:
            rendered.append(r"\texttt{" + escape_latex(part[1:-1]) + "}")
            continue
        escaped = escape_latex(part)
        escaped = re.sub(r"\*\*([^*]+)\*\*", r"\\textbf{\1}", escaped)
        escaped = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"\\textit{\1}", escaped)
        rendered.append(escaped)
    return "".join(rendered)


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


def _render_table(header_line: str, row_lines: list[str]) -> list[str]:
    header = _split_row(header_line)
    rows = [_split_row(line) for line in row_lines]
    column_count = max([len(header), *(len(row) for row in rows)])

    def padded(cells: list[str]) -> list[str]:
        return cells + [""] * (column_count - len(cells))

    out = [
        r"\begin{table}[h!]",
        r"\centering",
        r"\small",
        r"\begin{tabularx}{\textwidth}{" + " ".join(["X"] * column_count) + "}",
        r"\toprule",
        " & ".join(r"\textbf{" + _inline(cell) + "}" for cell in padded(header)) + r" \\",
        r"\midrule",
    ]
    for row in rows:
        out.append(" & ".join(_inline(cell) for cell in padded(row)) + r" \\")
    out.extend([r"\bottomrule", r"\end{tabularx}", r"\end{table}", ""])
    return out


def markdown_to_latex(text: str) -> str:
    """Converts a safe subset of Markdown into LaTeX formatted commands."""
    lines = text.strip().split("\n")
    output: list[str] = []
    paragraph: list[str] = []
    list_kind: str | None = None

    def close_list() -> None:
        nonlocal list_kind
        if list_kind is not None:
            output.append(f"\\end{{{list_kind}}}")
            output.append("")
            list_kind = None

    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            joined = " ".join(part.strip() for part in paragraph).strip()
            if joined:
                output.append(_inline(joined))
                output.append("")
            paragraph = []

    def open_list(kind: str) -> None:
        nonlocal list_kind
        if list_kind != kind:
            close_list()
            output.append(f"\\begin{{{kind}}}")
            list_kind = kind

    index = 0
    while index < len(lines):
        stripped = lines[index].strip()

        if not stripped:
            flush_paragraph()
            close_list()
            index += 1
            continue

        if (
            stripped.startswith("|")
            and index + 1 < len(lines)
            and _is_table_separator(lines[index + 1].strip())
        ):
            flush_paragraph()
            close_list()
            row_lines: list[str] = []
            index += 2
            while index < len(lines) and lines[index].strip().startswith("|"):
                row_lines.append(lines[index].strip())
                index += 1
            output.extend(_render_table(stripped, row_lines))
            continue

        heading = re.match(r"^(#{1,4})\s+(.*)$", stripped)
        if heading:
            flush_paragraph()
            close_list()
            level = len(heading.group(1))
            command = {
                1: "section*",
                2: "subsection*",
                3: "subsubsection*",
                4: "subsubsection*",
            }[level]
            output.append(f"\\{command}{{{_inline(heading.group(2))}}}")
            output.append("")
            index += 1
            continue

        if re.fullmatch(r"(-{3,}|\*{3,}|_{3,})", stripped):
            flush_paragraph()
            close_list()
            output.extend([r"\noindent\rule{\textwidth}{0.4pt}", ""])
            index += 1
            continue

        bullet = re.match(r"^[-*+]\s+(.*)$", stripped)
        if bullet:
            flush_paragraph()
            open_list("itemize")
            output.append(f"\\item {_inline(bullet.group(1))}")
            index += 1
            continue

        numbered = re.match(r"^\d+[.)]\s+(.*)$", stripped)
        if numbered:
            flush_paragraph()
            open_list("enumerate")
            output.append(f"\\item {_inline(numbered.group(1))}")
            index += 1
            continue

        if stripped.startswith(">"):
            flush_paragraph()
            close_list()
            output.extend(
                [
                    r"\begin{quote}",
                    _inline(stripped.lstrip("> ").strip()),
                    r"\end{quote}",
                    "",
                ]
            )
            index += 1
            continue

        close_list()
        paragraph.append(stripped)
        index += 1

    flush_paragraph()
    close_list()
    return "\n".join(output)


class LatexGenerator:
    def __init__(self, template_path: Path | None = None):
        if template_path is None:
            template_path = (
                Path(__file__).resolve().parent
                / "templates"
                / "latex"
                / "report.tex.j2"
            )
        self.template_path = template_path

    def render(self, report: ReportContent) -> str:
        template_content = self.template_path.read_text(encoding="utf-8")
        # Use LaTeX-safe Jinja2 delimiters to avoid conflicts with LaTeX braces/percent
        env = Environment(
            block_start_string=r"\BLOCK{",
            block_end_string="}",
            variable_start_string=r"\VAR{",
            variable_end_string="}",
            comment_start_string=r"\#{",
            comment_end_string="}",
            line_statement_prefix="%%",
            line_comment_prefix="%#",
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
        )
        template = env.from_string(template_content)

        rendered_sections = []
        for sec in report.sections:
            rendered_sections.append(
                {
                    "heading": escape_latex(sec.heading),
                    "body_latex": markdown_to_latex(sec.body_markdown),
                    "tables": [
                        {
                            "caption": escape_latex(table.caption),
                            "headers": [escape_latex(header) for header in table.headers],
                            "rows": [
                                [escape_latex(cell) for cell in row]
                                for row in table.rows
                            ],
                        }
                        for table in sec.tables
                    ],
                }
            )

        rendered_refs = [
            {
                "authors": escape_latex(reference.authors),
                "title": escape_latex(reference.title),
                "venue": escape_latex(reference.venue),
                "year": escape_latex(reference.year),
            }
            for reference in report.references
        ]

        front_page = None
        if report.front_page:
            page = report.front_page
            front_page = {
                "institution": escape_latex(page.institution),
                "university": escape_latex(page.university),
                "campus": escape_latex(page.campus),
                "department": escape_latex(page.department),
                "document_type": escape_latex(page.document_type),
                "title": escape_latex(page.title),
                "subtitle": escape_latex(page.subtitle),
                "course": escape_latex(page.course),
                "submitted_by": escape_latex(page.submitted_by),
                "roll_number": escape_latex(page.roll_number),
                "group": escape_latex(page.group),
                "program": escape_latex(page.program),
                "semester": escape_latex(page.semester),
                "section": escape_latex(page.section),
                "submitted_to": escape_latex(page.submitted_to),
                "date": escape_latex(page.date),
                "logo_path": escape_latex(page.logo_path.replace("\\", "/")),
            }

        return template.render(
            title=escape_latex(report.title),
            course=escape_latex(report.course),
            author=escape_latex(report.author or "Academic Assistant"),
            date=escape_latex(report.date or "2026"),
            abstract=escape_latex(report.abstract),
            sections=rendered_sections,
            references=rendered_refs,
            front_page=front_page,
            include_toc=report.include_toc,
        )
