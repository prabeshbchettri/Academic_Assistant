from __future__ import annotations

import logging
from typing import Any

from langgraph.types import interrupt

from ai.classifier import Classifier
from ai.evaluator import Evaluator
from ai.generator import SectionGenerator
from ai.llm.base import LLMProvider
from ai.retriever import RagRetriever
from configs.schema import CategoryConfig, load_category_config
from database.db import get_session
from database.repositories import (
    AssignmentRepository,
    AuditLogRepository,
    DocumentRepository,
)
from document.docx_generator import DocxGenerator
from document.pdf_exporter import PdfExporter
from integrations.normalizer import normalize_input
from models.assignment import (
    Category,
    NormalizedInput,
    RawInput,
)
from models.evaluation import DecisionType, HumanDecision
from models.report import ReportContent
from workflow.state import WorkflowState

logger = logging.getLogger(__name__)


def normalize_node(state: WorkflowState) -> dict[str, Any]:
    raw_dict = state.get("raw_input") or {}
    if isinstance(raw_dict, RawInput):
        raw = raw_dict
    elif isinstance(raw_dict, dict) and raw_dict:
        raw = RawInput.model_validate(raw_dict)
    else:
        raw = RawInput(source_type=SourceType.MANUAL, title="Academic Assignment")

    norm = normalize_input(raw)

    history = state.get("node_history", []) + ["normalize"]
    return {
        "normalized_input": norm.model_dump(mode="json"),
        "node_history": history,
        "status": "in_progress",
    }


def classify_node(state: WorkflowState, llm: LLMProvider) -> dict[str, Any]:
    norm_dict = state["normalized_input"]
    norm = NormalizedInput.model_validate(norm_dict)

    manual_cat_str = state.get("category")
    manual_cat = Category(manual_cat_str) if manual_cat_str else None

    classifier = Classifier(llm)
    res = classifier.classify(norm, manual_category=manual_cat)

    history = state.get("node_history", []) + ["classify"]
    return {
        "category": res.category.value,
        "node_history": history,
    }


def load_config_node(state: WorkflowState) -> dict[str, Any]:
    cat = state["category"]
    cfg = load_category_config(cat)
    history = state.get("node_history", []) + ["load_config"]
    return {
        "category_config": cfg.model_dump(mode="json"),
        "node_history": history,
    }


def check_missing_info_node(state: WorkflowState) -> dict[str, Any]:
    norm = NormalizedInput.model_validate(state["normalized_input"])
    cat = state["category"]

    # If it's a lab and has literally no numbers or procedures, flag missing info
    missing_questions = []
    text_lower = norm.cleaned_text.lower()
    if cat in ("initial_lab", "final_lab"):
        has_numbers = any(char.isdigit() for char in norm.cleaned_text)
        if not has_numbers and "user_provided_data" not in state:
            missing_questions.append("Experimental measurements/data: Please provide trial values or data tables.")

    history = state.get("node_history", []) + ["check_missing_info"]

    if missing_questions and not state.get("user_provided_data"):
        # Interrupt workflow and ask student for missing data
        user_response = interrupt({
            "type": "missing_info",
            "questions": missing_questions,
        })
        provided_text = ""
        if isinstance(user_response, dict):
            provided_text = user_response.get("provided_data") or user_response.get("details") or ""
        elif user_response:
            provided_text = str(user_response)

        return {
            "missing_info": {"is_missing": True, "questions": missing_questions},
            "user_provided_data": {"details": provided_text or "Simulated standard observations"},
            "node_history": history,
        }

    return {
        "missing_info": {"is_missing": False, "questions": []},
        "node_history": history,
    }


def retrieve_references_node(state: WorkflowState, llm: LLMProvider) -> dict[str, Any]:
    cfg = CategoryConfig.model_validate(state["category_config"])
    norm = NormalizedInput.model_validate(state["normalized_input"])
    chunks = []

    if cfg.rag.enabled:
        course = norm.course_name or "general"
        retriever = RagRetriever(llm=llm)
        chunks = retriever.retrieve(course, norm.title)

    history = state.get("node_history", []) + ["retrieve_references"]
    return {
        "retrieved_chunks": chunks,
        "node_history": history,
    }


def generate_content_node(state: WorkflowState, llm: LLMProvider) -> dict[str, Any]:
    cfg = CategoryConfig.model_validate(state["category_config"])
    norm = NormalizedInput.model_validate(state["normalized_input"])
    retrieved = state.get("retrieved_chunks", [])

    generator = SectionGenerator(llm)
    report = generator.generate_full_report(cfg, norm, retrieved_chunks=retrieved)

    history = state.get("node_history", []) + ["generate_content"]
    return {
        "report": report.model_dump(mode="json"),
        "node_history": history,
        "retry_count": state.get("retry_count", 0),
    }


def evaluate_output_node(state: WorkflowState, llm: LLMProvider) -> dict[str, Any]:
    cfg = CategoryConfig.model_validate(state["category_config"])
    report = ReportContent.model_validate(state["report"])

    evaluator = Evaluator(llm)
    eval_result = evaluator.evaluate_semantic(cfg, report)

    history = state.get("node_history", []) + ["evaluate_output"]
    return {
        "evaluation": eval_result.model_dump(mode="json"),
        "failed_sections": eval_result.failed_sections,
        "node_history": history,
    }


def regenerate_failed_node(state: WorkflowState, llm: LLMProvider) -> dict[str, Any]:
    cfg = CategoryConfig.model_validate(state["category_config"])
    norm = NormalizedInput.model_validate(state["normalized_input"])
    report = ReportContent.model_validate(state["report"])
    failed = state.get("failed_sections", [])
    retry_count = state.get("retry_count", 0) + 1

    generator = SectionGenerator(llm)
    new_sections = []

    for sec in report.sections:
        if sec.heading in failed or sec.heading.lower().replace(" ", "_") in failed:
            logger.info("Regenerating failed section '%s' (Attempt %d)", sec.heading, retry_count)
            draft = generator.generate_section(
                config=cfg,
                normalized=norm,
                section_name=sec.heading,
                prior_sections=new_sections,
                feedback="Previous attempt had issues. Please address rubric and word limits carefully.",
            )
            new_sections.append(draft)
        else:
            new_sections.append(sec)

    report.sections = new_sections
    history = state.get("node_history", []) + [f"regenerate_failed_attempt_{retry_count}"]

    return {
        "report": report.model_dump(mode="json"),
        "retry_count": retry_count,
        "node_history": history,
    }


def human_review_node(state: WorkflowState) -> dict[str, Any]:
    # Mandatory human approval interrupt before document export
    history = state.get("node_history", []) + ["human_review"]

    decision_data = interrupt({
        "type": "human_review",
        "report": state["report"],
        "evaluation": state["evaluation"],
    })

    if isinstance(decision_data, dict):
        decision = HumanDecision.model_validate(decision_data)
    else:
        decision = HumanDecision(decision=DecisionType.APPROVE)

    # Apply any direct text edits made by user
    if decision.decision == DecisionType.EDIT and decision.edited_sections:
        report = ReportContent.model_validate(state["report"])
        for sec in report.sections:
            if sec.heading in decision.edited_sections:
                sec.body_markdown = decision.edited_sections[sec.heading]
                sec.word_count = len(sec.body_markdown.split())
        return {
            "human_decision": decision.model_dump(mode="json"),
            "report": report.model_dump(mode="json"),
            "node_history": history,
        }

    return {
        "human_decision": decision.model_dump(mode="json"),
        "node_history": history,
    }


def export_node(state: WorkflowState) -> dict[str, Any]:
    report = ReportContent.model_validate(state["report"])
    cfg = CategoryConfig.model_validate(state["category_config"])
    assignment_id = state.get("assignment_id", 1)

    docx_gen = DocxGenerator()
    docx_path = docx_gen.generate(report, cfg, assignment_id=assignment_id)

    pdf_exporter = PdfExporter()
    pdf_path = pdf_exporter.export(report, docx_path, assignment_id=assignment_id)

    history = state.get("node_history", []) + ["export"]
    return {
        "docx_path": str(docx_path),
        "pdf_path": str(pdf_path) if pdf_path else "",
        "status": "approved",
        "node_history": history,
    }


def persist_node(state: WorkflowState) -> dict[str, Any]:
    assignment_id = state.get("assignment_id", 1)
    thread_id = state.get("thread_id", "default_thread")

    with get_session() as session:
        assign_repo = AssignmentRepository(session)
        assign_record = assign_repo.get_by_id(assignment_id)
        if assign_record is None:
            norm_title = state.get("normalized_input", {}).get("title", "Assignment")
            assign_record = assign_repo.create(
                title=norm_title,
                raw_text="",
                normalized_text="",
                content_hash="",
                status=state.get("status", "completed"),
            )
            assignment_id = assign_record.id or assignment_id
        else:
            assign_repo.update_status(assignment_id, state.get("status", "completed"))

        doc_repo = DocumentRepository(session)
        doc_repo.create(
            assignment_id=assignment_id,
            docx_path=state.get("docx_path", ""),
            pdf_path=state.get("pdf_path"),
            run_id=thread_id,
        )

        audit_repo = AuditLogRepository(session)
        audit_repo.log(
            event="workflow_completed",
            assignment_id=assignment_id,
            detail={"thread_id": thread_id, "category": state.get("category")},
        )

    history = state.get("node_history", []) + ["persist"]
    return {"node_history": history}
