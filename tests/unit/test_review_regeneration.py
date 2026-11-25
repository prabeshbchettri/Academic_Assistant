from __future__ import annotations

from ai.llm.mock import MockProvider
from configs.schema import load_category_config
from models.assignment import NormalizedInput, SourceType
from models.report import ReportContent, SectionDraft
from workflow.nodes import regenerate_failed_node
from workflow.state import WorkflowState


def _state(report: ReportContent, decision: dict) -> WorkflowState:
    cfg = load_category_config("assignment")
    normalized = NormalizedInput(
        title=report.title,
        cleaned_text="A short assignment prompt.",
        source_type=SourceType.MANUAL,
        content_hash="test-hash",
    )
    return {
        "category_config": cfg.model_dump(mode="json"),
        "normalized_input": normalized.model_dump(mode="json"),
        "report": report.model_dump(mode="json"),
        "failed_sections": ["Conclusion"],
        "human_decision": decision,
        "retry_count": 0,
    }


def _report() -> ReportContent:
    return ReportContent(
        title="Feedback Test",
        sections=[
            SectionDraft(heading="Introduction", body_markdown="old intro", word_count=2),
            SectionDraft(heading="Conclusion", body_markdown="old conclusion", word_count=2),
        ],
    )


def test_section_feedback_only_regenerates_requested_section() -> None:
    report = _report()
    result = regenerate_failed_node(
        _state(
            report,
            {
                "decision": "regenerate",
                "feedback": "Make the introduction shorter.",
                "regenerate_sections": ["Introduction"],
            },
        ),
        MockProvider(),
    )

    regenerated = ReportContent.model_validate(result["report"])
    assert regenerated.sections[0].body_markdown != "old intro"
    assert regenerated.sections[1].body_markdown == "old conclusion"


def test_overall_feedback_regenerates_every_section() -> None:
    report = _report()
    result = regenerate_failed_node(
        _state(
            report,
            {
                "decision": "regenerate",
                "feedback": "Tighten the whole document.",
                "regenerate_sections": [],
            },
        ),
        MockProvider(),
    )

    regenerated = ReportContent.model_validate(result["report"])
    assert regenerated.sections[0].body_markdown != "old intro"
    assert regenerated.sections[1].body_markdown != "old conclusion"
