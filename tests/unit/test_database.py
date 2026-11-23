import tempfile
from pathlib import Path

from database.db import get_engine, get_session, init_db
from database.repositories import (
    AssignmentRepository,
    AuditLogRepository,
    DocumentRepository,
    WorkflowRunRepository,
)


def test_database_repositories():
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        db_path = Path(tmp.name)
        engine = get_engine(db_path)
        init_db(db_path)

        with get_session(engine) as session:
            assign_repo = AssignmentRepository(session)
            assignment = assign_repo.create(
                title="Lab 1: Physics",
                raw_text="Measure velocity.",
                normalized_text="Measure velocity.",
                content_hash="hash123",
                category="initial_lab",
            )
            assert assignment.id is not None
            assert assignment.title == "Lab 1: Physics"

            retrieved = assign_repo.get_by_id(assignment.id)
            assert retrieved is not None
            assert retrieved.content_hash == "hash123"

            # Update status
            updated = assign_repo.update_status(assignment.id, "review")
            assert updated.status == "review"

            # Workflow run repository
            run_repo = WorkflowRunRepository(session)
            run = run_repo.save_or_update(
                thread_id="thread_test_1",
                assignment_id=assignment.id,
                status="in_progress",
                current_node="generate_content",
            )
            assert run.thread_id == "thread_test_1"

            # Document repository
            doc_repo = DocumentRepository(session)
            doc = doc_repo.create(
                assignment_id=assignment.id,
                docx_path="/tmp/report.docx",
                pdf_path="/tmp/report.pdf",
            )
            assert doc.id is not None
            docs = doc_repo.list_by_assignment(assignment.id)
            assert len(docs) == 1

            # Audit log repository
            audit_repo = AuditLogRepository(session)
            log = audit_repo.log("test_event", assignment_id=assignment.id, detail={"info": "ok"})
            assert log.id is not None
            logs = audit_repo.list_logs(assignment.id)
            assert len(logs) == 1
