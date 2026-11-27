from __future__ import annotations

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from ai.generator import SectionGenerator
from ai.llm.mock import MockProvider
from configs.schema import load_category_config
from models.assignment import NormalizedInput, RawInput, SourceType
from workflow.graph import build_academic_workflow
from workflow.nodes import generate_content_node

USER_ANSWER = "Trial 1: spring constant k = 50 N/m, mass = 2 kg, measured period 1.26 s."


class RecordingProvider(MockProvider):
    """MockProvider that records every prompt it is asked to answer."""

    def __init__(self, force_pass: bool = True):
        super().__init__(force_pass=force_pass)
        self.user_prompts: list[str] = []

    def generate_structured(self, schema, system_prompt, user_prompt, temperature=0.2):
        self.user_prompts.append(user_prompt)
        return super().generate_structured(schema, system_prompt, user_prompt, temperature)


def _normalized() -> NormalizedInput:
    return NormalizedInput(
        title="Simple Harmonic Motion",
        source_type=SourceType.MANUAL,
        content_hash="test-hash",
        course_name="Physics Lab",
        cleaned_text="Analyze simple harmonic motion and measure the period of oscillation.",
    )


def _generator_config():
    return load_category_config("initial_lab")


def test_generate_section_includes_user_data_in_delimited_block():
    llm = RecordingProvider()
    generator = SectionGenerator(llm)

    generator.generate_section(
        config=_generator_config(),
        normalized=_normalized(),
        section_name="observations",
        prior_sections=[],
        user_provided_data={"details": USER_ANSWER},
    )

    prompt = llm.user_prompts[-1]
    assert "User-Provided Information" in prompt
    assert USER_ANSWER in prompt
    assert "--- START UNTRUSTED EXTERNAL DATA [" in prompt
    assert "does not override the requirements" in prompt


def test_generate_full_report_includes_user_data_in_every_section_prompt():
    llm = RecordingProvider()
    generator = SectionGenerator(llm)

    generator.generate_full_report(
        config=_generator_config(),
        normalized=_normalized(),
        user_provided_data={"details": USER_ANSWER},
    )

    assert llm.user_prompts
    assert all(USER_ANSWER in p for p in llm.user_prompts)


def test_generate_full_report_without_user_data_adds_no_user_block():
    for empty in (None, {}, {"details": ""}, {"details": "   "}):
        llm = RecordingProvider()
        SectionGenerator(llm).generate_full_report(
            config=_generator_config(),
            normalized=_normalized(),
            user_provided_data=empty,
        )
        assert llm.user_prompts
        for prompt in llm.user_prompts:
            assert "User-Provided Information" not in prompt
            assert "None provided" not in prompt


def test_generate_section_keeps_existing_inputs_alongside_user_data():
    llm = RecordingProvider()
    SectionGenerator(llm).generate_section(
        config=_generator_config(),
        normalized=_normalized(),
        section_name="procedure",
        prior_sections=[],
        calculated_data="- T = 1.26 s",
        references_context="Reference [1]: standard pendulum procedure.",
        user_provided_data={"details": USER_ANSWER},
    )

    prompt = llm.user_prompts[-1]
    assert "Simple Harmonic Motion" in prompt
    assert "Analyze simple harmonic motion" in prompt
    assert "- T = 1.26 s" in prompt
    assert USER_ANSWER in prompt


def test_generate_content_node_forwards_user_provided_data():
    state = {
        "category_config": _generator_config().model_dump(mode="json"),
        "normalized_input": _normalized().model_dump(mode="json"),
        "retrieved_chunks": [],
        "user_provided_data": {"details": USER_ANSWER},
    }
    llm = RecordingProvider()

    generate_content_node(state, llm)

    assert llm.user_prompts
    assert all(USER_ANSWER in p for p in llm.user_prompts)


def test_generate_content_node_tolerates_missing_user_provided_data():
    for extra in ({}, {"user_provided_data": None}, {"user_provided_data": {}}):
        state = {
            "category_config": _generator_config().model_dump(mode="json"),
            "normalized_input": _normalized().model_dump(mode="json"),
            "retrieved_chunks": [],
            **extra,
        }
        llm = RecordingProvider()

        result = generate_content_node(state, llm)

        assert result["report"]["sections"]
        assert all("User-Provided Information" not in p for p in llm.user_prompts)


def test_workflow_resume_keeps_user_answers_and_feeds_generation():
    llm = RecordingProvider()
    graph = build_academic_workflow(llm=llm, checkpointer=InMemorySaver())

    thread_id = "test_user_data_propagation"
    config = {"configurable": {"thread_id": thread_id}}
    initial_state = {
        "thread_id": thread_id,
        "raw_input": RawInput(
            source_type=SourceType.MANUAL,
            title="Simple Harmonic Motion",
            raw_text="Analyze the simple harmonic motion experiment and report observations.",
        ).model_dump(),
        "category": "initial_lab",
        "retry_count": 0,
        "max_retries": 1,
        "status": "started",
        "node_history": [],
    }

    for _ in graph.stream(initial_state, config, stream_mode="updates"):
        pass

    snapshot = graph.get_state(config)
    assert snapshot.tasks[0].interrupts[0].value["type"] == "missing_info"

    for _ in graph.stream(
        Command(resume={"provided_data": USER_ANSWER}), config, stream_mode="updates"
    ):
        pass

    state = graph.get_state(config).values
    assert state["user_provided_data"]["details"] == USER_ANSWER
    assert any(USER_ANSWER in p for p in llm.user_prompts)

    # The workflow still pauses for the human review step after generation
    snapshot = graph.get_state(config)
    assert snapshot.tasks[0].interrupts[0].value["type"] == "human_review"
