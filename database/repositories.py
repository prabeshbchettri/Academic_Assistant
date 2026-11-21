from __future__ import annotations

import json
from typing import Any

from sqlmodel import Session, select

from database.models import (
    AssignmentTable,
    AuditLogTable,
    GeneratedDocumentTable,
    WorkflowRunTable,
    utc_now,
)


class AssignmentRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        title: str,
        raw_text: str,
        normalized_text: str,
        content_hash: str,
        source_type: str = "manual",
        source_id: str | None = None,
        category: str = "assignment",
        status: str = "pending",
    ) -> AssignmentTable:
        assignment = AssignmentTable(
            title=title,
            raw_text=raw_text,
            normalized_text=normalized_text,
            content_hash=content_hash,
            source_type=source_type,
            source_id=source_id,
            category=category,
            status=status,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        self.session.add(assignment)
        self.session.commit()
        self.session.refresh(assignment)
        return assignment

    def get_by_id(self, assignment_id: int) -> AssignmentTable | None:
        return self.session.get(AssignmentTable, assignment_id)

    def get_by_hash(self, content_hash: str) -> AssignmentTable | None:
        statement = select(AssignmentTable).where(AssignmentTable.content_hash == content_hash)
        return self.session.exec(statement).first()

    def list_all(self, limit: int = 50) -> list[AssignmentTable]:
        statement = select(AssignmentTable).order_by(AssignmentTable.created_at.desc()).limit(limit)  # type: ignore
        return list(self.session.exec(statement).all())

    def update_status(self, assignment_id: int, status: str) -> AssignmentTable | None:
        assignment = self.get_by_id(assignment_id)
        if assignment:
            assignment.status = status
            assignment.updated_at = utc_now()
            self.session.add(assignment)
            self.session.commit()
            self.session.refresh(assignment)
        return assignment


class WorkflowRunRepository:
    def __init__(self, session: Session):
        self.session = session

    def save_or_update(
        self,
        thread_id: str,
        assignment_id: int,
        status: str,
        current_node: str,
        retry_count: int = 0,
        state_dict: dict[str, Any] | None = None,
        error_message: str | None = None,
    ) -> WorkflowRunTable:
        state_json = json.dumps(state_dict or {})
        run = self.session.get(WorkflowRunTable, thread_id)
        if run is None:
            run = WorkflowRunTable(
                thread_id=thread_id,
                assignment_id=assignment_id,
                status=status,
                current_node=current_node,
                retry_count=retry_count,
                state_json=state_json,
                error_message=error_message,
                created_at=utc_now(),
                updated_at=utc_now(),
            )
        else:
            run.status = status
            run.current_node = current_node
            run.retry_count = retry_count
            run.state_json = state_json
            run.error_message = error_message
            run.updated_at = utc_now()

        self.session.add(run)
        self.session.commit()
        self.session.refresh(run)
        return run

    def get_by_thread_id(self, thread_id: str) -> WorkflowRunTable | None:
        return self.session.get(WorkflowRunTable, thread_id)

    def list_by_assignment(self, assignment_id: int) -> list[WorkflowRunTable]:
        statement = select(WorkflowRunTable).where(WorkflowRunTable.assignment_id == assignment_id)
        return list(self.session.exec(statement).all())


class DocumentRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        assignment_id: int,
        docx_path: str,
        pdf_path: str | None = None,
        version: int = 1,
        engine: str = "tectonic",
        run_id: str | None = None,
    ) -> GeneratedDocumentTable:
        doc = GeneratedDocumentTable(
            assignment_id=assignment_id,
            docx_path=docx_path,
            pdf_path=pdf_path,
            version=version,
            engine=engine,
            run_id=run_id,
            created_at=utc_now(),
        )
        self.session.add(doc)
        self.session.commit()
        self.session.refresh(doc)
        return doc

    def list_by_assignment(self, assignment_id: int) -> list[GeneratedDocumentTable]:
        statement = (
            select(GeneratedDocumentTable)
            .where(GeneratedDocumentTable.assignment_id == assignment_id)
            .order_by(GeneratedDocumentTable.version.desc())  # type: ignore
        )
        return list(self.session.exec(statement).all())


class AuditLogRepository:
    def __init__(self, session: Session):
        self.session = session

    def log(self, event: str, assignment_id: int | None = None, detail: dict[str, Any] | None = None) -> AuditLogTable:
        detail_json = json.dumps(detail or {})
        entry = AuditLogTable(
            assignment_id=assignment_id,
            event=event,
            detail_json=detail_json,
            created_at=utc_now(),
        )
        self.session.add(entry)
        self.session.commit()
        self.session.refresh(entry)
        return entry

    def list_logs(self, assignment_id: int | None = None, limit: int = 100) -> list[AuditLogTable]:
        query = select(AuditLogTable)
        if assignment_id is not None:
            query = query.where(AuditLogTable.assignment_id == assignment_id)
        query = query.order_by(AuditLogTable.created_at.desc()).limit(limit)  # type: ignore
        return list(self.session.exec(query).all())
