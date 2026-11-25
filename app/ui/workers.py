from __future__ import annotations

import logging
import uuid
from typing import Any

from langgraph.types import Command
from PySide6.QtCore import QObject, QThread, Signal

from ai.llm.base import LLMProvider
from ai.llm.factory import build_provider
from database.db import get_session
from database.repositories import AssignmentRepository, WorkflowRunRepository
from integrations.classroom.client import (
    build_classroom_service,
    list_courses,
    list_coursework,
)
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


class ClassroomCourseworkWorker(QThread):
    coursework_ready = Signal(list)
    error = Signal(str)

    def __init__(self, course_id: str, parent: QObject | None = None):
        super().__init__(parent)
        self.course_id = course_id

    def run(self) -> None:
        try:
            service = build_classroom_service()
            self.coursework_ready.emit(list_coursework(service, self.course_id))
        except Exception as exc:
            logger.exception("Could not load Classroom coursework: %s", exc)
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
            provider: LLMProvider = build_provider(use_mock=self.use_mock_llm)
            app_graph = build_academic_workflow(llm=provider)
            config = {"configurable": {"thread_id": self.thread_id}}

            if self.resume_command is None and self.raw_input is not None:
                editing_id = (self.raw_input.metadata or {}).get("editing_assignment_id")
                with get_session() as session:
                    repo = AssignmentRepository(session)
                    existing = (
                        repo.get_by_id(int(str(editing_id)))
                        if isinstance(editing_id, (int, str)) and str(editing_id).isdigit()
                        else None
                    )
                    if existing is not None:
                        self.assignment_id = existing.id or 1
                        repo.update_status(self.assignment_id, "in_progress")
                    else:
                        record = repo.create(
                            title=self.raw_input.title or "New Assignment",
                            raw_text=self.raw_input.raw_text,
                            normalized_text="",
                            content_hash="",
                            source_type=self.raw_input.source_type.value,
                            category=self.category or "assignment",
                        )
                        self.assignment_id = record.id or 1

                    WorkflowRunRepository(session).save_or_update(
                        thread_id=self.thread_id,
                        assignment_id=self.assignment_id,
                        status="started",
                        current_node="start",
                    )

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
                self.progress_signal.emit("resume", "Resuming workflow after human input...")
                stream = app_graph.stream(self.resume_command, config, stream_mode="updates")

            for chunk in stream:
                for node_name, _node_update in chunk.items():
                    msg = f"Completed node: {node_name}"
                    self.progress_signal.emit(node_name, msg)

            snapshot = app_graph.get_state(config)
            if snapshot.tasks:
                task = snapshot.tasks[0]
                if task.interrupts:
                    interrupt_val = task.interrupts[0].value
                    interrupt_type = (
                        interrupt_val.get("type", "unknown")
                        if isinstance(interrupt_val, dict)
                        else "unknown"
                    )
                    payload = interrupt_val if isinstance(interrupt_val, dict) else {}
                    with get_session() as session:
                        WorkflowRunRepository(session).save_or_update(
                            thread_id=self.thread_id,
                            assignment_id=self.assignment_id,
                            status="interrupted",
                            current_node=interrupt_type,
                        )
                    self.interrupt_signal.emit(interrupt_type, payload)
                    return

            final_state = dict(snapshot.values)
            self.resume_command = None
            self.raw_input = None
            self.finished_signal.emit(final_state)

        except Exception as exc:
            logger.exception("Workflow worker encountered an exception: %s", exc)
            self.resume_command = None
            try:
                with get_session() as session:
                    WorkflowRunRepository(session).save_or_update(
                        thread_id=self.thread_id or "unknown",
                        assignment_id=self.assignment_id,
                        status="error",
                        current_node="error",
                        error_message=str(exc)[:1000],
                    )
            except Exception:
                pass
            self.error_signal.emit(str(exc))
