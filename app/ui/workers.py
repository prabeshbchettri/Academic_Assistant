from __future__ import annotations

import logging
import uuid
from typing import Any

from langgraph.types import Command
from PySide6.QtCore import QObject, QThread, Signal

from ai.llm.base import LLMProvider
from ai.llm.gemini import GeminiProvider
from ai.llm.mock import MockProvider
from app.settings import settings
from database.db import get_session
from database.repositories import AssignmentRepository
from integrations.classroom.client import build_classroom_service, list_courses
from models.assignment import RawInput
from workflow.graph import build_academic_workflow
from workflow.state import WorkflowState

logger = logging.getLogger(__name__)


class ClassroomCoursesWorker(QThread):
    courses_ready = Signal(list)
    error = Signal(str)

    def run(self) -> None:
        try:
            service = build_classroom_service()
            self.courses_ready.emit(list_courses(service))
        except Exception as exc:
            logger.exception("Could not load Classroom courses: %s", exc)
            self.error.emit(str(exc))


class WorkflowWorker(QThread):
    progress_signal = Signal(str, str)  # node_name, status_message
    interrupt_signal = Signal(str, dict)  # interrupt_type, payload
    finished_signal = Signal(dict)  # final_state
    error_signal = Signal(str)  # error_message

    def __init__(self, parent: QObject | None = None, use_mock_llm: bool = False):
        super().__init__(parent)
        self.use_mock_llm = use_mock_llm
        self.raw_input: RawInput | None = None
        self.category: str | None = None
        self.thread_id: str = ""
        self.resume_command: Command | None = None
        self.assignment_id: int = 1

    def configure_new_run(self, raw_input: RawInput, category: str | None = None) -> str:
        self.raw_input = raw_input
        self.category = category
        self.thread_id = f"run_{uuid.uuid4().hex[:12]}"
        self.resume_command = None
        return self.thread_id

    def configure_resume(self, thread_id: str, resume_payload: Any) -> None:
        self.thread_id = thread_id
        self.resume_command = Command(resume=resume_payload)

    def run(self) -> None:
        try:
            # Select LLM provider
            if self.use_mock_llm or not settings.gemini_api_key_str:
                provider: LLMProvider = MockProvider()
            else:
                provider = GeminiProvider(api_key=settings.gemini_api_key_str)

            app_graph = build_academic_workflow(llm=provider)
            config = {"configurable": {"thread_id": self.thread_id}}

            # If starting a new run, persist initial assignment record in DB
            if self.resume_command is None and self.raw_input is not None:
                with get_session() as session:
                    repo = AssignmentRepository(session)
                    record = repo.create(
                        title=self.raw_input.title or "New Assignment",
                        raw_text=self.raw_input.raw_text,
                        normalized_text="",
                        content_hash="",
                        source_type=self.raw_input.source_type.value,
                        category=self.category or "assignment",
                    )
                    self.assignment_id = record.id or 1

                initial_state: WorkflowState = {
                    "assignment_id": self.assignment_id,
                    "thread_id": self.thread_id,
                    "raw_input": self.raw_input.model_dump(mode="json"),
                    "category": self.category or "",
                    "retry_count": 0,
                    "max_retries": 3,
                    "status": "started",
                    "node_history": [],
                }
                stream = app_graph.stream(initial_state, config, stream_mode="updates")
            else:
                # Resuming from interrupt
                self.progress_signal.emit("resume", "Resuming workflow after human input...")
                stream = app_graph.stream(self.resume_command, config, stream_mode="updates")

            for chunk in stream:
                for node_name, _node_update in chunk.items():
                    msg = f"Completed node: {node_name}"
                    self.progress_signal.emit(node_name, msg)

            # Check if workflow reached an interrupt or finished
            snapshot = app_graph.get_state(config)
            if snapshot.tasks:
                task = snapshot.tasks[0]
                if task.interrupts:
                    interrupt_val = task.interrupts[0].value
                    if isinstance(interrupt_val, dict):
                        interrupt_type = interrupt_val.get("type", "unknown")
                    else:
                        interrupt_type = "unknown"
                    payload = interrupt_val if isinstance(interrupt_val, dict) else {}
                    self.interrupt_signal.emit(interrupt_type, payload)
                    return

            final_state = dict(snapshot.values)
            self.resume_command = None
            self.raw_input = None
            self.finished_signal.emit(final_state)

        except Exception as exc:
            logger.exception("Workflow worker encountered an exception: %s", exc)
            self.resume_command = None
            self.error_signal.emit(str(exc))
