from __future__ import annotations

import argparse
import logging
import os
import sys

from app.logging_config import configure_logging
from app.settings import settings

logger = logging.getLogger(__name__)


def run_cli_generation(title: str, text: str, category: str = "assignment", mock: bool = False) -> None:
    from langgraph.types import Command

    from ai.llm.factory import build_llm_provider
    from database.db import get_session, init_db
    from database.repositories import AssignmentRepository
    from models.assignment import RawInput, SourceType
    from workflow.graph import build_academic_workflow
    from workflow.state import WorkflowState

    init_db()
    provider = build_llm_provider(use_mock=mock)
    graph = build_academic_workflow(llm=provider)

    with get_session() as session:
        repo = AssignmentRepository(session)
        rec = repo.create(
            title=title,
            raw_text=text,
            normalized_text="",
            content_hash="",
            source_type="manual",
            category=category,
        )
        assign_id = rec.id or 1

    thread_id = f"cli_{assign_id}"
    config = {"configurable": {"thread_id": thread_id}}

    state: WorkflowState = {
        "assignment_id": assign_id,
        "thread_id": thread_id,
        "raw_input": RawInput(source_type=SourceType.MANUAL, title=title, raw_text=text).model_dump(mode="json"),
        "category": category,
        "retry_count": 0,
        "max_retries": 3,
        "status": "started",
        "node_history": [],
    }

    print(f"Starting CLI run for '{title}' (Category: {category})...", flush=True)
    for chunk in graph.stream(state, config, stream_mode="updates"):
        for node in chunk.keys():
            print(f"  -> Finished step: {node}", flush=True)

    # Check for human review interrupt and auto-approve in CLI mode
    snapshot = graph.get_state(config)
    if snapshot.tasks and snapshot.tasks[0].interrupts:
        print("  -> Human review interrupt reached. Auto-approving for CLI export...", flush=True)
        resume_cmd = Command(resume={"decision": "approve"})
        for chunk in graph.stream(resume_cmd, config, stream_mode="updates"):
            for node in chunk.keys():
                print(f"  -> Finished step: {node}", flush=True)

    final_snapshot = graph.get_state(config)
    docx_path = final_snapshot.values.get("docx_path")
    pdf_path = final_snapshot.values.get("pdf_path")
    print("\nWorkflow Finished Successfully!", flush=True)
    print(f"  DOCX Output: {docx_path}", flush=True)
    print(f"  PDF Output:  {pdf_path}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Academic Document Preparation System")
    parser.add_argument("--cli", action="store_true", help="Run in headless CLI mode instead of GUI")
    parser.add_argument("--mock", action="store_true", help="Use deterministic mock LLM provider")
    parser.add_argument("--title", type=str, default="CLI Test Assignment", help="Assignment title for CLI mode")
    parser.add_argument(
        "--prompt",
        type=str,
        default="Discuss the fundamental concepts of Ohm's Law and calculate current when V = 12V and R = 4 ohms.",
        help="Assignment prompt text for CLI mode",
    )
    parser.add_argument("--category", type=str, default="assignment", help="Category: assignment, initial_lab, or final_lab")
    args = parser.parse_args()

    configure_logging()
    logger.info("Starting %s", settings.app_name)

    # If --cli specified or no DISPLAY environment variable on Linux, use CLI mode
    if args.cli or (sys.platform.startswith("linux") and not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY")):
        run_cli_generation(title=args.title, text=args.prompt, category=args.category, mock=args.mock)
        return

    # Otherwise launch PySide6 Desktop GUI
    from PySide6.QtWidgets import QApplication

    from app.ui.main_window import MainWindow

    app = QApplication(sys.argv)
    window = MainWindow(use_mock_llm=args.mock)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
