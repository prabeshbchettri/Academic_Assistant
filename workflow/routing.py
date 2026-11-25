from __future__ import annotations

from typing import Literal

from models.evaluation import DecisionType
from workflow.state import WorkflowState


def route_after_evaluation(
    state: WorkflowState,
) -> Literal["regenerate_failed", "human_review"]:
    eval_dict = state.get("evaluation", {})
    overall_passed = eval_dict.get("overall_passed", False)
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 3)

    if overall_passed:
        return "human_review"

    if retry_count < max_retries:
        return "regenerate_failed"

    # Max retries reached: proceed to human review with explicit warnings
    return "human_review"


def route_after_human_review(
    state: WorkflowState,
) -> Literal["export", "regenerate_failed", "human_review", "persist"]:
    decision_dict = state.get("human_decision", {})
    decision_type = decision_dict.get("decision", DecisionType.APPROVE)

    if decision_type == DecisionType.APPROVE:
        return "export"
    if decision_type == DecisionType.REGENERATE:
        return "regenerate_failed"
    if decision_type == DecisionType.EDIT:
        return "human_review"
    if decision_type == DecisionType.REJECT:
        return "persist"

    return "export"
