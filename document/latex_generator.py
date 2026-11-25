from __future__ import annotations

import re
from pathlib import Path

from jinja2 import Environment

from document.latex_escape import escape_latex, sanitize_math
from models.report import ReportContent

_MISSING_RE = re.compile(r"\[\[MISSING:\s*([^\]]+)\]\]")
_TABLE_SEPARATOR_RE = re.compile(r"^:?-{3,}:?$")
_INLINE_MATH_RE = re.compile(r"\$([^$\n]+?)\$")


def _prepare_text(text: str) -> str:
    return _MISSING_RE.sub(
        lambda match: f"[To be completed: {match.group(1).strip()}]",
        text,
    )


def _is_likely_math(expr: str) -> bool:
    """Distinguishes LaTeX inline math ($x^2$, $V = IR$) from currency ($100 budget)."""
    if not expr or expr[0].isspace() or expr[-1].isspace():
        return False
    # Pure number or price like "$100" or "$49.99" is currency, not math
    if re.fullmatch(r"\d+(?:[.,]\d+)?(?:\s*(?:k|m|b))?", expr.strip(), re.IGNORECASE):
        return False
    # Check if currency phrase like "100 budget"
    return not (re.match(r"^\d", expr.strip()) and not any(op in expr for op in "=+-*/^_\\<>"))


def _inline(text: str) -> str:
    """Escape prose while preserving inline Markdown (`code`, **bold**, *italic*) and $math$."""
    text = _prepare_text(text)
    tokens = re.split(
        r"(`[^`]+`|\$\d+(?:[.,]\d+)?(?=\s|[.,;:!?)]|$)|\$(?!\s)[^$\n]+?(?<!\s)\$)",
        text,
    )
    rendered: list[str] = []

    for token in tokens:
        if not token:
            continue
        if token.startswith("`") and token.endswith("`") and len(token) >= 2:
            rendered.append(r"\texttt{" + escape_latex(token[1:-1]) + "}")
            continue
        if token.startswith("$") and token.endswith("$") and len(token) >= 3:
            inner = token[1:-1]
            if _is_likely_math(inner):
                rendered.append(f"${sanitize_math(inner)}$")
                continue

        escaped = escape_latex(token)
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

    def normalized(cells: list[str]) -> list[str]:
        return (cells + [""] * column_count)[:column_count]

    out = [
        r"\begin{table}[H]",
        r"\centering",
        r"\footnotesize" if column_count >= 4 else r"\small",
        r"\begin{tabularx}{\textwidth}{"
        + " ".join([r">{\raggedright\arraybackslash}X"] * column_count)
        + "}",
        r"\toprule",
        " & ".join(
            r"\textbf{" + _inline(cell).replace("/", r"/\allowbreak ") + "}"
            for cell in normalized(header)
        )
        + r" \\",
        r"\midrule",
    ]
    for row in rows:
        out.append(
            " & ".join(
                _inline(cell).replace("/", r"/\allowbreak ") for cell in normalized(row)
            )
            + r" \\"
        )
    out.extend([r"\bottomrule", r"\end{tabularx}", r"\end{table}", ""])
    return out


def _render_code_block(code_lines: list[str]) -> list[str]:
    rendered_lines: list[str] = []
    for raw_line in code_lines:
        stripped_leading = len(raw_line) - len(raw_line.lstrip(" "))
        indent = r"\ " * min(stripped_leading, 16)
        escaped_body = escape_latex(raw_line.lstrip(" "))
        rendered_lines.append(f"{indent}{escaped_body}")
    joined = "\\\\\n".join(rendered_lines) if rendered_lines else r"\ "
    return [
        r"\begin{quote}",
        r"\ttfamily\footnotesize\raggedright",
        joined,
        r"\end{quote}",
        "",
    ]


def markdown_to_latex(text: str) -> str:
    """Converts Markdown (headings, lists, tables, fenced code blocks, math) to LaTeX."""
    lines = text.strip().split("\n")
    output: list[str] = []
    paragraph: list[str] = []
    list_kind: str | None = None
    in_code_block = False
    code_lines: list[str] = []
    in_display_math = False
    math_lines: list[str] = []

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
        raw_line = lines[index]
        stripped = raw_line.strip()

        if stripped.startswith("```"):
            flush_paragraph()
            close_list()
            if in_code_block:
                output.extend(_render_code_block(code_lines))
                code_lines.clear()
                in_code_block = False
            else:
                in_code_block = True
            index += 1
            continue

        if in_code_block:
            code_lines.append(raw_line.rstrip())
            index += 1
            continue

        # Single-line $$ ... $$ display math
        if stripped.startswith("$$") and stripped.endswith("$$") and len(stripped) > 4:
            flush_paragraph()
            close_list()
            expr = sanitize_math(stripped[2:-2].strip())
            output.extend([r"\[", expr, r"\]", ""])
            index += 1
            continue

        # Multi-line $$ ... $$ display math
        if stripped.startswith("$$"):
            flush_paragraph()
            close_list()
            if in_display_math:
                expr = sanitize_math("\n".join(math_lines).strip())
                output.extend([r"\[", expr, r"\]", ""])
                math_lines.clear()
                in_display_math = False
            else:
                in_display_math = True
                remainder = stripped[2:].strip()
                if remainder:
                    math_lines.append(remainder)
            index += 1
            continue

        if in_display_math:
            if stripped.endswith("$$"):
                tail = stripped[:-2].strip()
                if tail:
                    math_lines.append(tail)
                expr = sanitize_math("\n".join(math_lines).strip())
                output.extend([r"\[", expr, r"\]", ""])
                math_lines.clear()
                in_display_math = False
            else:
                math_lines.append(raw_line.strip())
            index += 1
            continue

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

    if in_code_block and code_lines:
        output.extend(_render_code_block(code_lines))
    if in_display_math and math_lines:
        output.extend([r"\[", sanitize_math("\n".join(math_lines).strip()), r"\]", ""])

    flush_paragraph()
    close_list()
    return "\n".join(output)


def _split_institution_campus(institution: str, campus: str) -> tuple[str, str]:
    inst = (institution or "").strip()
    camp = (campus or "").strip()
    if inst and camp and camp.lower() in inst.lower():
        stripped = re.sub(r",?\s*" + re.escape(camp), "", inst, flags=re.IGNORECASE).strip(" ,")
        if stripped:
            return stripped, camp
    return inst or "Institute of Engineering", camp


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

    def render(self, report: ReportContent, logo_override: str | None = None) -> str:
        template_content = self.template_path.read_text(encoding="utf-8")
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
            # Strip duplicate leading markdown heading matching the section heading
            cleaned_body = re.sub(
                r"^#{1,4}\s+" + re.escape(sec.heading) + r"\s*\n+",
                "",
                sec.body_markdown.strip(),
                flags=re.IGNORECASE,
            )
            rendered_tables = []
            for table in sec.tables:
                col_count = max(1, len(table.headers))
                clean_caption = re.sub(
                    r"^Table\s+\d+\s*[:.\-]\s*", "", table.caption.strip(), flags=re.IGNORECASE
                )
                padded_rows = [
                    [
                        escape_latex(cell).replace("/", r"/\allowbreak ")
                        for cell in (list(row) + [""] * col_count)[:col_count]
                    ]
                    for row in table.rows
                ]
                rendered_tables.append(
                    {
                        "caption": escape_latex(clean_caption),
                        "headers": [escape_latex(header) for header in table.headers],
                        "rows": padded_rows,
                    }
                )

            rendered_sections.append(
                {
                    "heading": escape_latex(sec.heading),
                    "body_latex": markdown_to_latex(cleaned_body),
                    "tables": rendered_tables,
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

        doc_prefs = (report.metadata or {}).get("document_preferences", {}) or {}
        font_family = str(doc_prefs.get("font_family") or "Times New Roman").strip()
        raw_font_size = int(doc_prefs.get("font_size") or 12)
        # Standard LaTeX article class supports 10pt, 11pt, 12pt cleanly
        font_size = min((10, 11, 12), key=lambda pt: abs(pt - raw_font_size))
        line_spacing = float(doc_prefs.get("line_spacing") or 1.25)
        margin_val = float(doc_prefs.get("margin_inches") or 1.0)
        margin_left = max(1.25, margin_val)

        front_page = None
        if report.front_page:
            page = report.front_page
            inst_clean, camp_clean = _split_institution_campus(page.institution, page.campus)
            effective_logo = logo_override if logo_override is not None else page.logo_path
            front_page = {
                "institution": escape_latex(inst_clean),
                "university": escape_latex(page.university),
                "campus": escape_latex(camp_clean),
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
                "logo_path": effective_logo.replace("\\", "/"),
            }

        def _truncate(s: str, limit: int = 38) -> str:
            s = s.strip()
            return s if len(s) <= limit else s[: limit - 3].rstrip() + "..."

        return template.render(
            title=escape_latex(report.title),
            header_title=escape_latex(_truncate(report.title, 38)),
            course=escape_latex(report.course),
            header_course=escape_latex(_truncate(report.course, 28)),
            author=escape_latex(report.author or "Academic Assistant"),
            date=escape_latex(report.date or "2026"),
            abstract=escape_latex(report.abstract),
            sections=rendered_sections,
            references=rendered_refs,
            front_page=front_page,
            include_toc=report.include_toc,
            font_family=font_family,
            font_size=font_size,
            line_spacing=f"{line_spacing:.2f}",
            margin_top=f"{margin_val:.2f}",
            margin_bottom=f"{margin_val:.2f}",
            margin_left=f"{margin_left:.2f}",
            margin_right=f"{margin_val:.2f}",
        )
