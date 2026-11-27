from __future__ import annotations

from typing import Literal

from models.evaluation import DecisionType, EvaluationStatus
from workflow.state import WorkflowState


def route_after_evaluation(state: WorkflowState) -> Literal["regenerate_failed", "human_review"]:
    eval_dict = state.get("evaluation") or {}
    status = eval_dict.get("status")
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 3)

    # Only an explicitly completed and passing evaluation can be accepted.
    if status == EvaluationStatus.PASSED.value and eval_dict.get("overall_passed") is True:
        return "human_review"

    if status == EvaluationStatus.FAILED.value:
        # Genuine quality failure: regenerate while attempts remain.
        if retry_count < max_retries:
            return "regenerate_failed"
        # Max retries reached: proceed to human review with a warning.
        return "human_review"

    # Inconclusive, missing, or unrecognised evaluation: never accept, never loop on
    # regeneration (regenerating content cannot repair a failed evaluation).
    return "human_review"


def route_after_human_review(state: WorkflowState) -> Literal["export", "regenerate_failed", "human_review"]:
    decision_dict = state.get("human_decision", {})
    decision_type = decision_dict.get("decision", DecisionType.APPROVE)

    if decision_type == DecisionType.APPROVE:
        return "export"
    elif decision_type == DecisionType.REGENERATE:
        return "regenerate_failed"
    elif decision_type == DecisionType.EDIT:
        # After editing, loop back for final confirmation or export directly
        return "export"

    return "export"
