from document.latex_escape import escape_latex, sanitize_math
from document.latex_generator import LatexGenerator
from models.report import Citation, ReportContent, SectionDraft


def test_latex_escape():
    raw = r"Formula & Results: 50% increase, $100 budget, #1 item, test_var, {x}, ~approx"
    escaped = escape_latex(raw)
    assert r"\&" in escaped
    assert r"\%" in escaped
    assert r"\$" in escaped
    assert r"\#" in escaped
    assert r"\_" in escaped
    assert r"\{" in escaped
    assert r"\}" in escaped


def test_sanitize_math():
    unsafe_math = r"\frac{a}{b} + \input{secret.tex} + \write18{rm -rf /}"
    safe_math = sanitize_math(unsafe_math)
    assert r"\frac{a}{b}" in safe_math
    assert r"\input" not in safe_math
    assert r"\write" not in safe_math


def test_latex_generator_render():
    gen = LatexGenerator()
    report = ReportContent(
        title="Modern Physics Lab & Analysis",
        course="PHYS 301",
        author="Alice Smith",
        date="2026",
        abstract="A concise abstract about physics.",
        sections=[
            SectionDraft(
                heading="Objective",
                body_markdown="Verify **Ohm's Law** and calculate *resistance*.",
                word_count=8,
            )
        ],
        references=[
            Citation(
                key="[1]",
                authors="A. Einstein",
                title="Relativity",
                year="1905",
                venue="Annalen der Physik",
            )
        ],
    )
    rendered = gen.render(report)
    assert r"\documentclass" in rendered
    assert r"Modern Physics Lab \& Analysis" in rendered
    assert r"\textbf{Ohm's Law}" in rendered
    assert r"\textit{resistance}" in rendered
