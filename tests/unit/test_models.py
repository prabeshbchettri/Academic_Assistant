from models.assignment import NormalizedInput, RawInput, SourceType
from models.evaluation import DecisionType, HumanDecision
from models.report import Citation, ReportContent, SectionDraft


def test_models_creation():
    raw = RawInput(source_type=SourceType.MANUAL, title="Physics 101", raw_text="Test prompt")
    assert raw.source_type == SourceType.MANUAL
    assert raw.title == "Physics 101"

    norm = NormalizedInput(
        title="Physics 101",
        cleaned_text="Test prompt",
        source_type=SourceType.MANUAL,
        content_hash="abc123hash",
    )
    assert norm.content_hash == "abc123hash"

    sec = SectionDraft(
        heading="Introduction",
        body_markdown="This is the intro with 8 words.",
        word_count=7,
        citations=["[1]"],
    )
    assert sec.heading == "Introduction"

    report = ReportContent(
        title="Physics Lab",
        sections=[sec],
        references=[Citation(key="[1]", authors="Newton", title="Principia", year="1687")],
    )
    assert report.total_word_count() == 7
    assert report.get_section("introduction") is not None

    decision = HumanDecision(decision=DecisionType.APPROVE)
    assert decision.decision == DecisionType.APPROVE
