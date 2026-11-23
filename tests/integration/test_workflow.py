import tempfile
from pathlib import Path

from langgraph.types import Command

from ai.llm.mock import MockProvider
from database.db import init_db
from models.assignment import RawInput, SourceType
from workflow.checkpointer import get_checkpointer
from workflow.graph import build_academic_workflow
from workflow.state import WorkflowState


def test_workflow_end_to_end_mock():
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        db_path = Path(tmp.name)
        init_db(db_path)
        checkpointer = get_checkpointer(db_path)

        # Create assignment in DB
        from database.db import get_engine, get_session
        from database.repositories import AssignmentRepository
        engine = get_engine(db_path)
        with get_session(engine) as session:
            repo = AssignmentRepository(session)
            rec = repo.create(
                title="Physics: Harmonic Oscillator",
                raw_text="Test prompt",
                normalized_text="",
                content_hash="h1",
                category="initial_lab",
            )
            assignment_id = rec.id or 1

        mock_llm = MockProvider(force_pass=True)
        graph = build_academic_workflow(llm=mock_llm, checkpointer=checkpointer)

        thread_id = "test_thread_happy_path"
        config = {"configurable": {"thread_id": thread_id}}

        initial_state: WorkflowState = {
            "assignment_id": assignment_id,
            "thread_id": thread_id,
            "raw_input": RawInput(
                source_type=SourceType.MANUAL,
                title="Physics: Harmonic Oscillator",
                raw_text="Analyze simple harmonic motion with k = 50 N/m and m = 2 kg. Measure period T.",
            ).model_dump(),
            "category": "initial_lab",
            "retry_count": 0,
            "max_retries": 3,
            "status": "started",
            "node_history": [],
        }

        # Run stream until interrupt (human review)
        for chunk in graph.stream(initial_state, config, stream_mode="updates"):
            pass

        snapshot = graph.get_state(config)
        assert snapshot.tasks
        assert snapshot.tasks[0].interrupts
        interrupt_val = snapshot.tasks[0].interrupts[0].value
        assert interrupt_val["type"] == "human_review"

        # Resume with human approval
        resume_cmd = Command(resume={"decision": "approve"})
        for chunk in graph.stream(resume_cmd, config, stream_mode="updates"):
            pass

        final_state = graph.get_state(config).values
        assert final_state["status"] == "approved"
        assert "docx_path" in final_state
        assert Path(final_state["docx_path"]).exists()
