from __future__ import annotations

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from pydantic import ValidationError

from ai.evaluator import Evaluator
from ai.llm.mock import MockProvider
from configs.schema import load_category_config
from models.assignment import RawInput, SourceType
from models.evaluation import (
    EvaluationResult,
    EvaluationStatus,
    SectionEvaluation,
    SectionScore,
)
from models.report import Citation, ReportContent, SectionDraft
from workflow.graph import build_academic_workflow
from workflow.routing import route_after_evaluation

SECTION_WORD_COUNTS = {
    "objective": 80,
    "apparatus": 50,
    "procedure": 150,
    "observations": 100,
    "calculations": 100,
    "results": 100,
    "discussion": 200,
    "conclusion": 80,
}


def _valid_report() -> ReportContent:
    sections = [
        SectionDraft(
            heading=heading.title(),
            body_markdown="Content supported by the supplied measurements [1].",
            word_count=words,
            citations=["[1]"],
        )
        for heading, words in SECTION_WORD_COUNTS.items()
    ]
    return ReportContent(
        title="Simple Harmonic Motion",
        sections=sections,
        references=[
            Citation(key="[1]", authors="A. Author", title="Lab Manual", year="2024"),
            Citation(key="[2]", authors="B. Author", title="Physics Notes", year="2023"),
            Citation(key="[3]", authors="C. Author", title="Lab Standards", year="2022"),
        ],
    )


def _failing_evaluation() -> EvaluationResult:
    return EvaluationResult(
        status=EvaluationStatus.FAILED,
        overall_passed=False,
        deterministic_passed=False,
        semantic_passed=False,
        overall_score=0.3,
        section_evaluations=[
            SectionEvaluation(
                section_heading="Section",
                scores=[SectionScore(criterion_id="clarity", score=0.3, comments="Unclear")],
                passed=False,
            )
        ],
    )


class QualityFailProvider(MockProvider):
    """Returns a genuine failing section verdict."""

    def generate_structured(self, schema, system_prompt, user_prompt, temperature=0.2):
        if schema is EvaluationResult:
            return _failing_evaluation()
        return super().generate_structured(schema, system_prompt, user_prompt, temperature)


class RaisingProvider(MockProvider):
    """Simulates a provider outage / timeout."""

    def __init__(self) -> None:
        super().__init__(force_pass=True)
        self.evaluation_calls = 0

    def generate_structured(self, schema, system_prompt, user_prompt, temperature=0.2):
        if schema is EvaluationResult:
            self.evaluation_calls += 1
            raise RuntimeError("provider is unavailable")
        return super().generate_structured(schema, system_prompt, user_prompt, temperature)


class InvalidOutputProvider(MockProvider):
    """Simulates structured output that cannot satisfy the EvaluationResult contract."""

    def generate_structured(self, schema, system_prompt, user_prompt, temperature=0.2):
        if schema is EvaluationResult:
            return EvaluationResult.model_validate(
                {"overall_passed": True, "deterministic_passed": True, "semantic_passed": True}
            )
        return super().generate_structured(schema, system_prompt, user_prompt, temperature)


class EmptySectionEvaluationProvider(MockProvider):
    """Simulates an incomplete response that omits the per-section verdict."""

    def generate_structured(self, schema, system_prompt, user_prompt, temperature=0.2):
        if schema is EvaluationResult:
            return EvaluationResult(
                status=EvaluationStatus.PASSED,
                overall_passed=True,
                deterministic_passed=True,
                semantic_passed=True,
                overall_score=1.0,
                section_evaluations=[],
            )
        return super().generate_structured(schema, system_prompt, user_prompt, temperature)


def _config():
    return load_category_config("initial_lab")


# A. Successful evaluation
def test_valid_report_and_valid_evaluator_response_pass():
    result = Evaluator(MockProvider(force_pass=True)).evaluate_semantic(_config(), _valid_report())

    assert result.status == EvaluationStatus.PASSED
    assert result.overall_passed is True
    assert result.deterministic_passed is True
    assert result.semantic_passed is True
    assert len(result.section_evaluations) == len(SECTION_WORD_COUNTS)


# B. Genuine quality failure
def test_genuine_quality_failure_is_failed_not_passed():
    result = Evaluator(QualityFailProvider(force_pass=False)).evaluate_semantic(
        _config(), _valid_report()
    )

    assert result.status == EvaluationStatus.FAILED
    assert result.overall_passed is False
    assert result.failed_sections
    assert result.overall_score != 0.92


# C. Provider exception
def test_provider_exception_produces_inconclusive_not_passing_result():
    result = Evaluator(RaisingProvider()).evaluate_semantic(_config(), _valid_report())

    assert result.status == EvaluationStatus.INCONCLUSIVE
    assert result.overall_passed is False
    assert result.semantic_passed is False
    assert result.overall_score == 0.0
    assert result.section_evaluations == []
    assert "RuntimeError" in result.general_feedback
    assert "could not be completed" in result.general_feedback


# D. Invalid response
def test_invalid_evaluator_output_cannot_pass():
    result = Evaluator(InvalidOutputProvider()).evaluate_semantic(_config(), _valid_report())

    assert result.status == EvaluationStatus.INCONCLUSIVE
    assert result.overall_passed is False
    assert result.overall_score == 0.0
    assert "ValidationError" in result.general_feedback


def test_evaluator_response_without_section_verdict_is_inconclusive():
    result = Evaluator(EmptySectionEvaluationProvider()).evaluate_semantic(
        _config(), _valid_report()
    )

    assert result.status == EvaluationStatus.INCONCLUSIVE
    assert result.overall_passed is False
    assert "no section evaluation" in result.general_feedback


# E. Empty report
def test_empty_report_cannot_pass_evaluation():
    result = Evaluator(MockProvider(force_pass=True)).evaluate_semantic(
        _config(), ReportContent(title="Empty", sections=[], references=[])
    )

    assert result.status == EvaluationStatus.FAILED
    assert result.overall_passed is False
    assert result.semantic_passed is False
    assert result.overall_score == 0.0
    assert "no sections" in result.general_feedback


# F. Missing evaluation result
def test_passing_verdict_without_status_cannot_validate():
    with pytest.raises(ValidationError):
        EvaluationResult(overall_passed=True, deterministic_passed=True, semantic_passed=True)


def test_missing_or_null_evaluation_state_does_not_pass_routing():
    for state in (
        {},
        {"evaluation": None},
        {"evaluation": {"overall_passed": True}},
        {"evaluation": {"status": "unknown", "overall_passed": True}},
    ):
        assert route_after_evaluation(state) == "human_review"


# G. Workflow routing
def test_routing_distinguishes_pass_quality_failure_and_inconclusive():
    passed = {
        "evaluation": {"status": "passed", "overall_passed": True},
        "retry_count": 0,
        "max_retries": 3,
    }
    failed = {
        "evaluation": {"status": "failed", "overall_passed": False},
        "retry_count": 0,
        "max_retries": 3,
    }
    failed_exhausted = {**failed, "retry_count": 3}
    inconclusive = {
        "evaluation": {"status": "inconclusive", "overall_passed": False},
        "retry_count": 0,
        "max_retries": 3,
    }

    assert route_after_evaluation(passed) == "human_review"
    assert route_after_evaluation(failed) == "regenerate_failed"
    assert route_after_evaluation(failed_exhausted) == "human_review"
    # Evaluation execution failure must not consume retries or trigger regeneration.
    assert route_after_evaluation(inconclusive) == "human_review"


def _run_workflow(provider, max_retries: int = 1):
    graph = build_academic_workflow(llm=provider, checkpointer=InMemorySaver())
    thread_id = f"eval-{type(provider).__name__}-{max_retries}"
    config = {"configurable": {"thread_id": thread_id}}
    initial_state = {
        "thread_id": thread_id,
        "raw_input": RawInput(
            source_type=SourceType.MANUAL,
            title="Thermodynamics Essay",
            raw_text="Write an essay on the laws of thermodynamics with worked examples.",
        ).model_dump(),
        "category": "assignment",
        "retry_count": 0,
        "max_retries": max_retries,
        "status": "started",
        "node_history": [],
    }

    for _ in graph.stream(initial_state, config, stream_mode="updates"):
        pass

    snapshot = graph.get_state(config)
    assert snapshot.tasks[0].interrupts[0].value["type"] == "human_review"
    return snapshot.values


# H. Retry limit + workflow-level handling of evaluator execution failure
def test_evaluator_execution_failure_stops_at_review_without_retry_loop():
    provider = RaisingProvider()
    state = _run_workflow(provider, max_retries=3)

    assert state["evaluation"]["status"] == "inconclusive"
    assert state["evaluation"]["overall_passed"] is False
    assert state["evaluation"]["section_evaluations"] == []
    assert state["evaluation"]["overall_score"] == 0.0
    assert state["errors"]
    assert state["node_history"].count("evaluate_output") == 1
    assert not any(h.startswith("regenerate_failed") for h in state["node_history"])


def test_quality_failure_retries_are_bounded_by_max_retries():
    state = _run_workflow(QualityFailProvider(force_pass=False), max_retries=2)

    assert state["evaluation"]["status"] == "failed"
    assert state["evaluation"]["overall_passed"] is False
    assert state["node_history"].count("evaluate_output") == 3
    assert sum(h.startswith("regenerate_failed") for h in state["node_history"]) == 2
