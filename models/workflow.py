from __future__ import annotations

from pydantic import BaseModel


class WorkflowRunRecord(BaseModel):
    thread_id: str
    assignment_id: int
    status: str
    current_node: str
    retry_count: int = 0
    state_json: str = "{}"
    error_message: str | None = None
