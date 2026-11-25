from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel

from ai.evaluator import Evaluator
from ai.llm.base import LLMProvider
from ai.llm.mock import MockProvider
from ai.llm.router import ResilientLLMRouter
from ai.retriever import sanitize_collection_name
from configs.schema import load_category_config
from document.docx_generator import _effective_formatting
from document.latex_generator import LatexGenerator, markdown_to_latex
from models.assignment import NormalizedInput, SourceType
from models.evaluation import DecisionType
from models.report import Citation, FrontPage, ReportContent, SectionDraft, TableData
from workflow.nodes import check_missing_info_node, generate_content_node, human_review_node
from workflow.routing import route_after_human_review
from workflow.state import WorkflowState

T = TypeVar("T", bound=BaseModel)


class _FailingProvider(LLMProvider):
    def generate_structured(
        self,
        schema: type[T],
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
    ) -> T:
        raise RuntimeError("Primary API 429 exhausted")

    def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.4,
    ) -> str:
        raise RuntimeError("Primary API 429 exhausted")

    def embed(self, texts: list[str]) -> list[list[float]]:
        raise RuntimeError("Primary API 429 exhausted")


def test_resilient_router_failover_and_telemetry() -> None:
    router = ResilientLLMRouter(
        providers=[("nvidia", _FailingProvider()), ("mock", MockProvider())]
    )
    out = router.generate_text("system", "Summarize Ohm's law.")
    assert "Mock response" in out

    summary = router.telemetry.summary()
    assert summary["total_calls"] == 2
    assert summary["failed_calls"] == 1
    assert summary["successful_calls"] == 1
    assert summary["fallback_activations"] == 1
    assert "mock" in summary["providers_used"]


def test_evaluator_does_not_fail_open_on_llm_error() -> None:
    cfg = load_category_config("assignment")
    ev = Evaluator(llm=_FailingProvider())
    report = ReportContent(
        title="Test",
        sections=[
            SectionDraft(heading="Introduction", body_markdown="Too short", word_count=2),
        ],
        references=[Citation(key="[1]", authors="Course", title="Brief", year="2026")],
    )
    res = ev.evaluate_semantic(cfg, report)
    assert res.overall_passed is False
    assert "Introduction" in res.failed_sections
    assert any(f.check_name == "semantic_eval_degraded" for f in res.deterministic_findings)
    assert res.overall_score < 0.7


def test_missing_info_data_reaches_generation(monkeypatch) -> None:
    cfg = load_category_config("initial_lab")
    norm = NormalizedInput(
        title="Lab 2: Circuit Verification",
        cleaned_text="Lab 2: Verify circuit resistance without numbers.",
        source_type=SourceType.MANUAL,
        content_hash="abc",
    )

    monkeypatch.setattr(
        "workflow.nodes.interrupt",
        lambda payload: {"provided_data": "Trial 1: V = 12 V, I = 3 A, R = V / I"},
    )
    state: WorkflowState = {
        "category": "initial_lab",
        "category_config": cfg.model_dump(mode="json"),
        "normalized_input": norm.model_dump(mode="json"),
        "node_history": [],
    }

    after_check = check_missing_info_node(state)
    updated_norm = NormalizedInput.model_validate(after_check["normalized_input"])
    assert "V = 12 V" in updated_norm.cleaned_text
    assert "V = 12 V" in updated_norm.metadata["assignment_notes"]

    state.update(after_check)  # type: ignore[arg-type]
    after_gen = generate_content_node(state, MockProvider())
    report = ReportContent.model_validate(after_gen["report"])
    assert report.references and report.references[0].authors != "J. Smith, R. Taylor"


def test_human_review_preserves_edits_on_approve_and_loops_on_edit(monkeypatch) -> None:
    cfg = load_category_config("assignment")
    report = ReportContent(
        title="Edits Test",
        sections=[SectionDraft(heading="Introduction", body_markdown="Original", word_count=1)],
        references=[Citation(key="[1]", authors="Course", title="Spec", year="2026")],
    )
    state: WorkflowState = {
        "category_config": cfg.model_dump(mode="json"),
        "report": report.model_dump(mode="json"),
        "evaluation": {
            "overall_passed": False,
            "deterministic_passed": False,
            "semantic_passed": True,
        },
        "node_history": [],
    }

    monkeypatch.setattr(
        "workflow.nodes.interrupt",
        lambda payload: {
            "decision": DecisionType.APPROVE,
            "edited_sections": {"Introduction": "Student edited text before approve"},
        },
    )
    res_approve = human_review_node(state)
    approved_report = ReportContent.model_validate(res_approve["report"])
    assert approved_report.sections[0].body_markdown == "Student edited text before approve"
    assert route_after_human_review({**state, **res_approve}) == "export"  # type: ignore[arg-type]

    monkeypatch.setattr(
        "workflow.nodes.interrupt",
        lambda payload: {
            "decision": DecisionType.EDIT,
            "edited_sections": {"Introduction": "Intermediate student draft"},
        },
    )
    res_edit = human_review_node(state)
    assert route_after_human_review({**state, **res_edit}) == "human_review"  # type: ignore[arg-type]


def test_latex_code_math_tables_and_front_page_preferences() -> None:
    md = (
        "Budget is $100 while Ohm's law states $V = I \\times R$.\n\n"
        "$$P = I^2 R$$\n\n"
        "```python\n"
        "def ohm_current(v, r):\n"
        "    return v / r\n"
        "```"
    )
    tex_body = markdown_to_latex(md)
    assert r"\$100" in tex_body
    assert r"$V = I \times R$" in tex_body
    assert r"\[" in tex_body and "P = I^2 R" in tex_body
    assert r"\ttfamily" in tex_body
    assert r"ohm\_current" in tex_body

    report = ReportContent(
        title="Format Test",
        front_page=FrontPage(
            institution="Institute of Engineering, Pulchowk Campus",
            campus="Pulchowk Campus",
            submitted_by="Subesh Yadav",
            roll_number="080BCT084",
            group="D",
            program="B.E. Computer",
            semester="V",
            section="AB",
            date="November 25, 2026",
        ),
        sections=[
            SectionDraft(
                heading="Results",
                body_markdown=md,
                tables=[TableData(caption="T1", headers=["A", "B", "C"], rows=[["1", "2"]])],
            )
        ],
        metadata={
            "document_preferences": {
                "font_family": "Times New Roman",
                "font_size": 12,
                "line_spacing": 1.5,
                "margin_inches": 1.0,
            }
        },
    )
    rendered = LatexGenerator().render(report)
    assert "Program:" not in rendered
    assert "Semester:" not in rendered
    assert "Department of Electronics \\& Computer Engineering" in rendered
    assert "1 & 2 &  \\\\" in rendered

    cfg = load_category_config("assignment")
    eff = _effective_formatting(report, cfg)
    assert eff.formatting.font_size == 12
    assert eff.formatting.line_spacing == 1.5


def test_sanitize_collection_name() -> None:
    name = sanitize_collection_name("Data Structures & Algorithms (CT 552)!")
    assert 3 <= len(name) <= 63
    assert " " not in name and "&" not in name and "(" not in name
    assert len(sanitize_collection_name("A")) >= 3


def test_evaluator_incremental_cache_skips_unchanged_sections() -> None:
    class _CountingMock(MockProvider):
        def __init__(self) -> None:
            super().__init__(force_pass=True)
            self.calls = 0

        def generate_structured(self, schema, system_prompt, user_prompt, temperature=0.2):
            self.calls += 1
            return super().generate_structured(schema, system_prompt, user_prompt, temperature)

    cfg = load_category_config("assignment")
    llm = _CountingMock()
    ev = Evaluator(llm=llm)
    report = ReportContent(
        title="Cache Test",
        sections=[
            SectionDraft(heading="Introduction", body_markdown="Intro " * 120, word_count=120),
            SectionDraft(heading="Conclusion", body_markdown="Conc " * 100, word_count=100),
        ],
        references=[Citation(key="[1]", authors="Course", title="Brief", year="2026")],
    )
    first_eval = ev.evaluate_semantic(cfg, report)
    assert llm.calls == 2

    llm.calls = 0
    second_eval = ev.evaluate_semantic(
        cfg,
        report,
        previous_evaluation=first_eval,
        changed_sections={"conclusion"},
    )
    assert llm.calls == 1
    assert len(second_eval.section_evaluations) == 2
