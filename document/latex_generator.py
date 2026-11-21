from __future__ import annotations

import re
from pathlib import Path

from jinja2 import Template

from document.latex_escape import escape_latex
from models.report import ReportContent


def markdown_to_latex(text: str) -> str:
    """Converts a safe subset of Markdown into LaTeX formatted commands."""
    lines = text.strip().split("\n")
    tex_lines = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            tex_lines.append("")
            continue

        if stripped.startswith("### "):
            tex_lines.append(f"\\subsubsection*{{{escape_latex(stripped[4:])}}}")
        elif stripped.startswith("## "):
            tex_lines.append(f"\\subsection*{{{escape_latex(stripped[3:])}}}")
        elif stripped.startswith(("- ", "* ")):
            escaped_item = escape_latex(stripped[2:])
            tex_lines.append(f"\\item {escaped_item}")
        elif re.match(r"^\d+\.\s+", stripped):
            item_text = re.sub(r"^\d+\.\s+", "", stripped)
            tex_lines.append(f"\\item {escape_latex(item_text)}")
        else:
            # Inline bold/italics
            escaped = escape_latex(stripped)
            # Bold: **bold** -> \textbf{...}
            escaped = re.sub(r"\*\*([^*]+)\*\*", r"\\textbf{\1}", escaped)
            # Italics: *italic* -> \textit{...}
            escaped = re.sub(r"\*([^*]+)\*", r"\\textit{\1}", escaped)
            tex_lines.append(escaped + "\n")

    return "\n".join(tex_lines)


class LatexGenerator:
    def __init__(self, template_path: Path | None = None):
        if template_path is None:
            template_path = Path(__file__).resolve().parent / "templates" / "latex" / "report.tex.j2"
        self.template_path = template_path

    def render(self, report: ReportContent) -> str:
        template_content = self.template_path.read_text(encoding="utf-8")
        template = Template(template_content)

        rendered_sections = []
        for sec in report.sections:
            rendered_sections.append({
                "heading": escape_latex(sec.heading),
                "body_latex": markdown_to_latex(sec.body_markdown),
                "tables": [
                    {
                        "caption": escape_latex(t.caption),
                        "headers": [escape_latex(h) for h in t.headers],
                        "rows": [[escape_latex(cell) for cell in row] for row in t.rows],
                    }
                    for t in sec.tables
                ],
            })

        rendered_refs = [
            {
                "authors": escape_latex(r.authors),
                "title": escape_latex(r.title),
                "venue": escape_latex(r.venue),
                "year": escape_latex(r.year),
            }
            for r in report.references
        ]

        return template.render(
            title=escape_latex(report.title),
            author=escape_latex(report.author or "Academic Assistant"),
            date=escape_latex(report.date or "2026"),
            abstract=escape_latex(report.abstract),
            sections=rendered_sections,
            references=rendered_refs,
        )
