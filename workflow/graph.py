from __future__ import annotations

from functools import partial

from langgraph.graph import END, START, StateGraph

from ai.llm.base import LLMProvider
from ai.llm.mock import MockProvider
from workflow.checkpointer import get_checkpointer
from workflow.nodes import (
    check_missing_info_node,
    classify_node,
    evaluate_output_node,
    export_node,
    generate_content_node,
    human_review_node,
    load_config_node,
    normalize_node,
    persist_node,
    regenerate_failed_node,
    retrieve_references_node,
)
from workflow.routing import route_after_evaluation, route_after_human_review
from workflow.state import WorkflowState


def build_academic_workflow(llm: LLMProvider | None = None, checkpointer=None):
    provider = llm or MockProvider()
    builder = StateGraph(WorkflowState)

    builder.add_node("normalize", normalize_node)
    builder.add_node("classify", partial(classify_node, llm=provider))
    builder.add_node("load_config", load_config_node)
    builder.add_node("check_missing_info", check_missing_info_node)
    builder.add_node("retrieve_references", partial(retrieve_references_node, llm=provider))
    builder.add_node("generate_content", partial(generate_content_node, llm=provider))
    builder.add_node("evaluate_output", partial(evaluate_output_node, llm=provider))
    builder.add_node("regenerate_failed", partial(regenerate_failed_node, llm=provider))
    builder.add_node("human_review", human_review_node)
    builder.add_node("export", export_node)
    builder.add_node("persist", persist_node)

    builder.add_edge(START, "normalize")
    builder.add_edge("normalize", "classify")
    builder.add_edge("classify", "load_config")
    builder.add_edge("load_config", "check_missing_info")
    builder.add_edge("check_missing_info", "retrieve_references")
    builder.add_edge("retrieve_references", "generate_content")
    builder.add_edge("generate_content", "evaluate_output")

    builder.add_conditional_edges(
        "evaluate_output",
        route_after_evaluation,
        {
            "regenerate_failed": "regenerate_failed",
            "human_review": "human_review",
        },
    )
    builder.add_edge("regenerate_failed", "evaluate_output")

    builder.add_conditional_edges(
        "human_review",
        route_after_human_review,
        {
            "export": "export",
            "regenerate_failed": "regenerate_failed",
            "human_review": "human_review",
            "persist": "persist",
        },
    )

    builder.add_edge("export", "persist")
    builder.add_edge("persist", END)

    saver = checkpointer if checkpointer is not None else get_checkpointer()
    return builder.compile(checkpointer=saver)
