from __future__ import annotations

from typing import Any, TypedDict


class WorkflowState(TypedDict, total=False):
    assignment_id: int
    thread_id: str
    raw_input: dict[str, Any]
    normalized_input: dict[str, Any]
    category: str
    category_config: dict[str, Any]
    missing_info: dict[str, Any]
    user_provided_data: dict[str, Any]
    references: list[dict[str, Any]]
    retrieved_chunks: list[str]
    report: dict[str, Any]
    evaluation: dict[str, Any]
    retry_count: int
    max_retries: int
    failed_sections: list[str]
    human_decision: dict[str, Any]
    status: str  # in_progress, interrupted_missing_info, interrupted_review, approved, failed
    node_history: list[str]
    errors: list[str]
    docx_path: str
    pdf_path: str
