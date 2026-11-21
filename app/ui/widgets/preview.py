from __future__ import annotations

import markdown
from PySide6.QtWidgets import QTextBrowser, QVBoxLayout, QWidget

from models.report import ReportContent


class DocumentPreviewWidget(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(True)
        layout.addWidget(self.browser)

    def display_report(self, report_dict: dict) -> None:
        try:
            report = ReportContent.model_validate(report_dict)
        except Exception:
            self.browser.setPlainText(str(report_dict))
            return

        md_parts = [
            f"# {report.title}\n",
            f"**Course:** {report.course} | **Date:** {report.date} | **Author:** {report.author}\n",
            "---\n",
        ]

        if report.abstract:
            md_parts.append(f"### Abstract\n*{report.abstract}*\n")

        for sec in report.sections:
            md_parts.append(f"## {sec.heading}\n")
            md_parts.append(sec.body_markdown + "\n")

            if sec.tables:
                for t in sec.tables:
                    md_parts.append(f"*{t.caption}*\n")
                    header_line = "| " + " | ".join(t.headers) + " |"
                    sep_line = "| " + " | ".join(["---"] * len(t.headers)) + " |"
                    row_lines = ["| " + " | ".join(r) + " |" for r in t.rows]
                    md_parts.append("\n".join([header_line, sep_line] + row_lines) + "\n")

        if report.references:
            md_parts.append("## References\n")
            for r in report.references:
                md_parts.append(f"- **{r.key}** {r.authors}, *{r.title}*, {r.venue}, {r.year}.\n")

        full_md = "\n".join(md_parts)
        html = markdown.markdown(full_md, extensions=["tables", "fenced_code"])

        # Styled HTML
        styled_html = f"""
        <html>
        <head>
        <style>
            body {{ font-family: 'Liberation Serif', Georgia, serif; line-height: 1.6; color: #1a202c; padding: 20px; }}
            h1 {{ color: #1B365D; border-bottom: 2px solid #E2E8F0; padding-bottom: 8px; font-size: 24px; }}
            h2 {{ color: #2D3748; margin-top: 24px; font-size: 18px; }}
            h3 {{ color: #4A5568; font-size: 15px; }}
            table {{ border-collapse: collapse; width: 100%; margin: 16px 0; }}
            th, td {{ border: 1px solid #CBD5E1; padding: 8px 12px; text-align: left; }}
            th {{ background-color: #F1F5F9; font-weight: bold; }}
            code {{ background-color: #EDF2F7; padding: 2px 6px; border-radius: 4px; font-family: monospace; }}
            blockquote {{ border-left: 4px solid #CBD5E1; margin: 0; padding-left: 16px; color: #718096; }}
        </style>
        </head>
        <body>{html}</body>
        </html>
        """
        self.browser.setHtml(styled_html)
