from __future__ import annotations

import docx

from ai.evaluator import Evaluator
from ai.generator import SectionGenerator
from ai.llm.mock import MockProvider
from configs.schema import load_category_config
from document.docx_generator import DocxGenerator
from document.latex_generator import LatexGenerator
from models.assignment import NormalizedInput, SourceType
from models.report import Citation, ReferenceProvenance, ReportContent, SectionDraft


class RecordingProvider(MockProvider):
    def __init__(self) -> None:
        super().__init__(force_pass=True)
        self.user_prompts: list[str] = []

    def generate_structured(self, schema, system_prompt, user_prompt, temperature=0.2):
        self.user_prompts.append(user_prompt)
        return super().generate_structured(schema, system_prompt, user_prompt, temperature)


def _normalized() -> NormalizedInput:
    return NormalizedInput(
        title="Reference Integrity",
        source_type=SourceType.MANUAL,
        content_hash="ref-hash",
        course_name="Physics Lab",
        cleaned_text="Analyze the experiment and report the observations.",
    )


def _report(*, ref_keys: list[str], citations: list[str], body_extra: str = "") -> ReportContent:
    limits = {
        "introduction": 100,
        "main_content": 400,
        "analysis": 150,
        "conclusion": 80,
    }
    sections = [
        SectionDraft(
            heading=heading.title(),
            body_markdown=f"Supported statement [1].{body_extra}",
            word_count=words,
            citations=list(citations),
        )
        for heading, words in limits.items()
    ]
    references = [
        Citation(key=key, authors="A. Author", title=f"Source {key}", year="2024")
        for key in ref_keys
    ]
    return ReportContent(title="Reference Integrity", sections=sections, references=references)


def _simple_report(references: list[Citation]) -> ReportContent:
    return ReportContent(
        title="Reference Rendering",
        sections=[
            SectionDraft(
                heading="Introduction",
                body_markdown="A short body without citations.",
                word_count=6,
            )
        ],
        references=references,
    )


# A. No references
def test_generation_without_references_produces_empty_bibliography():
    report = SectionGenerator(MockProvider()).generate_full_report(
        load_category_config("assignment"), _normalized()
    )

    assert report.references == []
    assert "Foundations of Modern Experimental Analysis" not in report.model_dump_json()
    assert "Standard Laboratory Procedures" not in report.model_dump_json()


# B. Supplied references
def test_generation_keeps_supplied_references_and_exposes_them_to_the_prompt():
    llm = RecordingProvider()
    supplied = [
        Citation(
            key="[1]",
            authors="A. Author",
            title="Real Source",
            year="2020",
            venue="Real Press",
            doi="10.1000/real",
            source="user-provided",
        )
    ]

    report = SectionGenerator(llm).generate_full_report(
        load_category_config("assignment"), _normalized(), references=supplied
    )

    assert [(r.key, r.title) for r in report.references] == [("[1]", "Real Source")]
    assert report.references[0].doi == "10.1000/real"
    assert report.references[0].source == "user-provided"
    assert llm.user_prompts
    assert all('[1] A. Author, "Real Source", Real Press, 2020.' in p for p in llm.user_prompts)


# C. Missing metadata
def test_incomplete_reference_metadata_is_preserved_without_inventing_details():
    sparse = Citation(key="[2]", authors="", title="", year="2021", venue="")

    report = SectionGenerator(MockProvider()).generate_full_report(
        load_category_config("assignment"), _normalized(), references=[sparse]
    )

    stored = report.references[0]
    assert stored.authors == ""
    assert stored.title == ""
    assert stored.venue == ""
    assert stored.doi == ""
    assert stored.url == ""
    assert stored.provenance == ReferenceProvenance.UNVERIFIED


# D. Unsupported citations
def test_citations_without_a_supplied_reference_are_flagged():
    report = _report(ref_keys=["[1]"], citations=["[2]"], body_extra=" Compare with [7].")

    passed, findings = Evaluator(MockProvider()).run_deterministic_checks(
        load_category_config("assignment"), report
    )

    citation_findings = [f for f in findings if f.check_name == "citation_validity"]
    messages = " ".join(f.message for f in citation_findings)
    assert passed is False
    assert "'[2]'" in messages
    assert "'[7]'" in messages


def test_valid_citations_have_no_citation_findings():
    report = _report(ref_keys=["[1]", "[2]"], citations=["[1]"])

    _, findings = Evaluator(MockProvider()).run_deterministic_checks(
        load_category_config("assignment"), report
    )

    assert not [f for f in findings if f.check_name == "citation_validity"]


# E. LLM-generated suggestions
def test_llm_suggested_reference_never_enters_the_bibliography():
    supplied = Citation(key="[1]", authors="A. Author", title="Real Source", year="2020")
    suggestion = Citation(
        key="[9]",
        authors="Fake Author",
        title="Invented Paper",
        year="2025",
        provenance=ReferenceProvenance.LLM_SUGGESTION,
    )

    report = SectionGenerator(MockProvider()).generate_full_report(
        load_category_config("assignment"), _normalized(), references=[supplied, suggestion]
    )

    assert [r.key for r in report.references] == ["[1]"]
    assert "Invented Paper" not in report.model_dump_json()


def test_only_llm_suggestions_leaves_the_bibliography_empty():
    suggestion = Citation(
        key="[9]",
        authors="Fake Author",
        title="Invented Paper",
        year="2025",
        provenance=ReferenceProvenance.LLM_SUGGESTION,
    )

    report = SectionGenerator(MockProvider()).generate_full_report(
        load_category_config("assignment"), _normalized(), references=[suggestion]
    )

    assert report.references == []


# F. Duplicate references
def test_duplicate_references_are_collapsed_keeping_the_first_entry():
    first = Citation(key="[1]", authors="First", title="First Source", year="2020")
    duplicate = Citation(key="[1]", authors="Second", title="Second Source", year="2021")

    report = SectionGenerator(MockProvider()).generate_full_report(
        load_category_config("assignment"), _normalized(), references=[first, duplicate]
    )

    assert len(report.references) == 1
    assert report.references[0].title == "First Source"


# Minimum reference requirement
def test_reference_requirement_reports_shortfall_without_manufacturing_entries():
    cfg = load_category_config("assignment")
    evaluator = Evaluator(MockProvider())

    insufficient = _report(ref_keys=["[1]"], citations=["[1]"])
    passed, findings = evaluator.run_deterministic_checks(cfg, insufficient)

    shortfall = [f for f in findings if f.check_name == "references_min_count"]
    assert passed is False
    assert len(shortfall) == 1
    assert "must not be invented" in shortfall[0].message
    assert len(insufficient.references) == 1

    sufficient = _report(ref_keys=["[1]", "[2]"], citations=["[1]"])
    passed_enough, findings_enough = evaluator.run_deterministic_checks(cfg, sufficient)
    assert not [f for f in findings_enough if f.check_name == "references_min_count"]
    assert passed_enough is True


# G. DOCX rendering
def test_docx_empty_bibliography_renders_without_fabricated_entries():
    path = DocxGenerator().generate(
        _simple_report([]), load_category_config("assignment"), assignment_id=99101, version=1
    )
    text = "\n".join(p.text for p in docx.Document(str(path)).paragraphs)

    assert "References" not in text
    assert "Smith" not in text
    assert "Johnson" not in text


def test_docx_renders_supplied_references_without_filling_missing_fields():
    references = [
        Citation(
            key="[1]", authors="A. Author", title="Real Source", year="2020", venue="Real Press"
        ),
        Citation(key="[2]", authors="B. Author", title="Sparse Source", year="2021"),
    ]
    path = DocxGenerator().generate(
        _simple_report(references),
        load_category_config("assignment"),
        assignment_id=99102,
        version=1,
    )
    text = "\n".join(p.text for p in docx.Document(str(path)).paragraphs)

    assert "References" in text
    assert '[1] A. Author, "Real Source", Real Press, 2020.' in text
    assert '[2] B. Author, "Sparse Source", 2021.' in text
    assert ", ," not in text


# H. PDF rendering (LaTeX source used for PDF compilation)
def test_latex_empty_bibliography_has_no_entries():
    rendered = LatexGenerator().render(_simple_report([]))

    assert "thebibliography" not in rendered
    assert "J. Smith" not in rendered
    assert "M. Johnson" not in rendered


def test_latex_renders_supplied_references():
    references = [Citation(key="[1]", authors="A. Author", title="Real Source", year="2020")]
    rendered = LatexGenerator().render(_simple_report(references))

    assert "\\begin{thebibliography}" in rendered
    assert "A. Author" in rendered
    assert "Real Source" in rendered
