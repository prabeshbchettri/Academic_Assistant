from __future__ import annotations

import logging
import re
from typing import Any

from langgraph.types import interrupt

from ai.calculations import extract_and_evaluate_formulas
from ai.classifier import Classifier
from ai.evaluator import Evaluator, format_section_feedback
from ai.generator import SectionGenerator, build_grounded_references
from ai.llm.base import LLMProvider
from ai.retriever import RagRetriever
from configs.schema import CategoryConfig, load_category_config
from database.db import get_session
from database.repositories import (
    AssignmentRepository,
    AuditLogRepository,
    DocumentRepository,
    WorkflowRunRepository,
)
from document.docx_generator import DocxGenerator
from document.pdf_exporter import PdfExporter
from integrations.normalizer import normalize_input
from models.assignment import (
    Category,
    NormalizedInput,
    RawInput,
    SourceType,
)
from models.evaluation import DecisionType, EvaluationResult, HumanDecision
from models.report import ReportContent, SectionDraft
from workflow.state import WorkflowState

logger = logging.getLogger(__name__)

_MEASUREMENT_RE = re.compile(
    r"(?:"
    r"=\s*[-+]?\d"
    r"|[-+]?\d+(?:\.\d+)?\s*(?:v|mv|kv|a|ma|ohm|ohms|ω|hz|khz|mhz|m|cm|mm|km|kg|g|s|ms|n|pa|j|w|kw|db|deg|°|%)"
    r"|\btrial\s*\d+"
    r")",
    re.IGNORECASE,
)


def _has_experimental_data(norm: NormalizedInput) -> bool:
    notes = str((norm.metadata or {}).get("assignment_notes") or "")
    combined = f"{norm.cleaned_text}\n{notes}"
    if _MEASUREMENT_RE.search(combined):
        return True
    # Strip likely header/title/course code tokens on the first line before counting raw numbers
    lines = norm.cleaned_text.splitlines()
    body = "\n".join(lines[1:]) if len(lines) > 1 else ""
    body_plus_notes = f"{body}\n{notes}"
    numeric_tokens = re.findall(r"\b\d+(?:\.\d+)?\b", body_plus_notes)
    return len(numeric_tokens) >= 2


def _collect_telemetry(llm: LLMProvider) -> dict[str, Any]:
    tracker = getattr(llm, "telemetry", None)
    if tracker is not None and hasattr(tracker, "summary"):
        return dict(tracker.summary())
    return {}


def _apply_edited_sections(report: ReportContent, edited_sections: dict[str, str]) -> bool:
    changed = False
    for sec in report.sections:
        if sec.heading in edited_sections:
            new_body = edited_sections[sec.heading]
            if new_body != sec.body_markdown:
                sec.body_markdown = new_body
                sec.word_count = len(new_body.split())
                changed = True
    return changed


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
    norm = NormalizedInput.model_validate(state["normalized_input"])

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

    missing_questions: list[str] = []
    if (
        cat in ("initial_lab", "final_lab")
        and not _has_experimental_data(norm)
        and "user_provided_data" not in state
    ):
        missing_questions.append(
            "Experimental measurements/data: Please provide trial values, "
            "apparatus specs, or data tables."
        )

    history = state.get("node_history", []) + ["check_missing_info"]

    if missing_questions and not state.get("user_provided_data"):
        user_response = interrupt({
            "type": "missing_info",
            "questions": missing_questions,
        })
        provided_text = ""
        if isinstance(user_response, dict):
            provided_text = str(
                user_response.get("provided_data") or user_response.get("details") or ""
            ).strip()
        elif user_response:
            provided_text = str(user_response).strip()

        final_provided = provided_text or "Simulate standard realistic observations."
        # Inject user-provided measurements directly into normalized_input for generator & evaluator
        if provided_text and "simulate standard" not in provided_text.lower():
            norm.cleaned_text = (
                f"{norm.cleaned_text}\n\n"
                f"[Student Provided Experimental Data]\n{final_provided}"
            ).strip()
            meta = dict(norm.metadata or {})
            existing_notes = str(meta.get("assignment_notes") or "").strip()
            meta["assignment_notes"] = (
                f"{existing_notes}\n{final_provided}".strip()
                if existing_notes
                else final_provided
            )
            norm.metadata = meta

        return {
            "normalized_input": norm.model_dump(mode="json"),
            "missing_info": {"is_missing": True, "questions": missing_questions},
            "user_provided_data": {"details": final_provided},
            "node_history": history,
        }

    return {
        "missing_info": {"is_missing": False, "questions": []},
        "node_history": history,
    }


def retrieve_references_node(state: WorkflowState, llm: LLMProvider) -> dict[str, Any]:
    cfg = CategoryConfig.model_validate(state["category_config"])
    norm = NormalizedInput.model_validate(state["normalized_input"])
    chunks: list[str] = []
    sources: list[dict[str, Any]] = []

    if cfg.rag.enabled:
        course = norm.course_name or "general"
        retriever = RagRetriever(llm=llm)
        retrieved = retriever.retrieve_with_sources(course, norm.title)
        chunks = [item.text for item in retrieved]
        sources = [item.model_dump(mode="json") for item in retrieved]

    history = state.get("node_history", []) + ["retrieve_references"]
    return {
        "retrieved_chunks": chunks,
        "retrieved_sources": sources,
        "node_history": history,
    }


def generate_content_node(state: WorkflowState, llm: LLMProvider) -> dict[str, Any]:
    cfg = CategoryConfig.model_validate(state["category_config"])
    norm = NormalizedInput.model_validate(state["normalized_input"])
    retrieved_chunks = state.get("retrieved_chunks", [])
    retrieved_sources = state.get("retrieved_sources", [])

    generator = SectionGenerator(llm)
    report = generator.generate_full_report(
        cfg,
        norm,
        retrieved_chunks=retrieved_chunks,
        retrieved_sources=retrieved_sources,
    )

    history = state.get("node_history", []) + ["generate_content"]
    return {
        "report": report.model_dump(mode="json"),
        "llm_telemetry": _collect_telemetry(llm),
        "node_history": history,
        "retry_count": state.get("retry_count", 0),
    }


def evaluate_output_node(state: WorkflowState, llm: LLMProvider) -> dict[str, Any]:
    cfg = CategoryConfig.model_validate(state["category_config"])
    norm = NormalizedInput.model_validate(state["normalized_input"])
    report = ReportContent.model_validate(state["report"])

    prev_eval_dict = state.get("evaluation")
    prev_eval = EvaluationResult.model_validate(prev_eval_dict) if prev_eval_dict else None
    regen_list = state.get("last_regenerated_sections")
    changed = {s.lower() for s in regen_list} if regen_list else None

    evaluator = Evaluator(llm)
    eval_result = evaluator.evaluate_semantic(
        cfg,
        report,
        normalized=norm,
        previous_evaluation=prev_eval,
        changed_sections=changed,
    )

    history = state.get("node_history", []) + ["evaluate_output"]
    return {
        "evaluation": eval_result.model_dump(mode="json"),
        "failed_sections": eval_result.failed_sections,
        "last_regenerated_sections": [],
        "llm_telemetry": _collect_telemetry(llm),
        "node_history": history,
    }


def regenerate_failed_node(state: WorkflowState, llm: LLMProvider) -> dict[str, Any]:
    cfg = CategoryConfig.model_validate(state["category_config"])
    norm = NormalizedInput.model_validate(state["normalized_input"])
    report = ReportContent.model_validate(state["report"])
    failed = list(state.get("failed_sections", []))
    retry_count = state.get("retry_count", 0) + 1

    eval_dict = state.get("evaluation") or {}
    eval_obj = EvaluationResult.model_validate(eval_dict) if eval_dict else None

    decision = state.get("human_decision") or {}
    student_feedback = ""
    requested_sections: list[str] = []
    if isinstance(decision, dict):
        student_feedback = (decision.get("feedback") or "").strip()
        requested_sections = [
            str(name)
            for name in (decision.get("regenerate_sections") or [])
            if str(name).strip()
        ]

    if requested_sections:
        failed = requested_sections
    elif student_feedback:
        failed = [sec.heading for sec in report.sections]

    formulas = extract_and_evaluate_formulas(norm.cleaned_text)
    calc_summary = "\n".join(
        f"- {f['variable']} = {f['expression']} => {f['value']}" for f in formulas
    )
    retrieved_sources = state.get("retrieved_sources", [])
    if retrieved_sources:
        ref_context = "\n".join(
            f"[{idx}] ({src.get('source', 'Material')}): {src.get('text', '')}"
            for idx, src in enumerate(retrieved_sources, start=1)
        )
    else:
        ref_context = "\n".join(state.get("retrieved_chunks", []))

    grounded_refs = report.references or build_grounded_references(
        norm, retrieved_sources=retrieved_sources
    )
    available_refs_text = "\n".join(
        f"{r.key} {r.authors}, {r.title} ({r.venue}, {r.year})" for r in grounded_refs
    )
    valid_ref_keys = {r.key.strip() for r in grounded_refs}

    generator = SectionGenerator(llm)
    new_sections: list[SectionDraft] = []
    regenerated_headings: list[str] = []
    failed_lower = {item.lower().replace("_", " ") for item in failed}

    for sec in report.sections:
        sec_norm = sec.heading.lower().replace("_", " ")
        if sec.heading in failed or sec_norm in failed_lower:
            logger.info("Regenerating section '%s' (Attempt %d)", sec.heading, retry_count)
            regenerated_headings.append(sec.heading)
            section_critique = (
                format_section_feedback(eval_obj, sec.heading) if eval_obj else ""
            )
            feedback_parts = [
                "Previous attempt failed quality gates. "
                "Strictly address the rubric and word count bounds."
            ]
            if section_critique:
                feedback_parts.append(f"Automated evaluator findings:\n{section_critique}")
            if student_feedback:
                feedback_parts.append(f"Student feedback to address:\n{student_feedback}")

            draft = generator.generate_section(
                config=cfg,
                normalized=norm,
                section_name=sec.heading,
                prior_sections=new_sections,
                calculated_data=calc_summary,
                references_context=ref_context,
                feedback="\n\n".join(feedback_parts),
                available_references=available_refs_text,
            )
            draft.citations = [c for c in draft.citations if c.strip() in valid_ref_keys]
            new_sections.append(draft)
        else:
            new_sections.append(sec)

    report.sections = new_sections
    history = state.get("node_history", []) + [f"regenerate_failed_attempt_{retry_count}"]

    return {
        "report": report.model_dump(mode="json"),
        "retry_count": retry_count,
        "last_regenerated_sections": regenerated_headings,
        "llm_telemetry": _collect_telemetry(llm),
        "node_history": history,
    }


def human_review_node(state: WorkflowState) -> dict[str, Any]:
    history = state.get("node_history", []) + ["human_review"]

    decision_data = interrupt({
        "type": "human_review",
        "report": state["report"],
        "evaluation": state["evaluation"],
        "telemetry": state.get("llm_telemetry", {}),
    })

    if isinstance(decision_data, dict):
        decision = HumanDecision.model_validate(decision_data)
    else:
        decision = HumanDecision(decision=DecisionType.APPROVE)

    report = ReportContent.model_validate(state["report"])
    edits_applied = False
    if decision.edited_sections:
        edits_applied = _apply_edited_sections(report, decision.edited_sections)

    updates: dict[str, Any] = {
        "human_decision": decision.model_dump(mode="json"),
        "node_history": history,
    }
    if edits_applied or decision.decision == DecisionType.EDIT:
        updates["report"] = report.model_dump(mode="json")
        # Refresh deterministic verification checks when edits were applied
        if state.get("category_config") and state.get("evaluation"):
            cfg = CategoryConfig.model_validate(state["category_config"])
            eval_obj = EvaluationResult.model_validate(state["evaluation"])
            det_passed, findings = Evaluator(llm=None).run_deterministic_checks(cfg, report)  # type: ignore[arg-type]
            eval_obj.deterministic_passed = det_passed
            eval_obj.deterministic_findings = findings
            det_failed = [f.section for f in findings if not f.passed and f.section]
            eval_obj.failed_sections = list(dict.fromkeys(det_failed))
            eval_obj.overall_passed = det_passed and len(eval_obj.failed_sections) == 0
            updates["evaluation"] = eval_obj.model_dump(mode="json")

    if decision.decision == DecisionType.REJECT:
        updates["status"] = "rejected"

    return updates


def export_node(state: WorkflowState) -> dict[str, Any]:
    report = ReportContent.model_validate(state["report"])
    cfg = CategoryConfig.model_validate(state["category_config"])
    assignment_id = state.get("assignment_id", 1)

    version = state.get("version")
    if not version:
        with get_session() as session:
            existing_docs = DocumentRepository(session).list_by_assignment(assignment_id)
            version = (existing_docs[0].version + 1) if existing_docs else 1

    docx_gen = DocxGenerator()
    docx_path = docx_gen.generate(report, cfg, assignment_id=assignment_id, version=version)

    pdf_exporter = PdfExporter()
    pdf_path = pdf_exporter.export(
        report, docx_path, assignment_id=assignment_id, version=version
    )

    history = state.get("node_history", []) + ["export"]
    return {
        "version": version,
        "docx_path": str(docx_path),
        "pdf_path": str(pdf_path) if pdf_path else "",
        "pdf_engine": getattr(pdf_exporter, "last_engine", "tectonic"),
        "status": "approved",
        "node_history": history,
    }


def persist_node(state: WorkflowState) -> dict[str, Any]:
    assignment_id = state.get("assignment_id", 1)
    thread_id = state.get("thread_id", "default_thread")
    final_status = state.get("status", "completed")

    with get_session() as session:
        assign_repo = AssignmentRepository(session)
        assign_record = assign_repo.get_by_id(assignment_id)
        if assign_record is None:
            norm_title = state.get("normalized_input", {}).get("title", "Assignment")
            norm_text = state.get("normalized_input", {}).get("cleaned_text", "")
            content_hash = state.get("normalized_input", {}).get("content_hash", "")
            assign_record = assign_repo.create(
                title=norm_title,
                raw_text=norm_text,
                normalized_text=norm_text,
                content_hash=content_hash,
                status=final_status,
            )
            assignment_id = assign_record.id or assignment_id
        else:
            assign_repo.update_status(assignment_id, final_status)

        if state.get("docx_path"):
            doc_repo = DocumentRepository(session)
            doc_repo.create(
                assignment_id=assignment_id,
                docx_path=state.get("docx_path", ""),
                pdf_path=state.get("pdf_path"),
                version=int(state.get("version") or 1),
                engine=state.get("pdf_engine") or "tectonic",
                run_id=thread_id,
            )

        run_repo = WorkflowRunRepository(session)
        run_repo.save_or_update(
            thread_id=thread_id,
            assignment_id=assignment_id,
            status="completed" if final_status == "approved" else final_status,
            current_node="persist",
            retry_count=int(state.get("retry_count") or 0),
            state_dict={
                "category": state.get("category"),
                "version": state.get("version", 1),
                "pdf_engine": state.get("pdf_engine", ""),
                "telemetry": state.get("llm_telemetry", {}),
                "node_history": state.get("node_history", []),
            },
        )

        audit_repo = AuditLogRepository(session)
        audit_repo.log(
            event="workflow_completed",
            assignment_id=assignment_id,
            detail={
                "thread_id": thread_id,
                "category": state.get("category"),
                "status": final_status,
                "version": state.get("version", 1),
                "telemetry": state.get("llm_telemetry", {}),
            },
        )

    history = state.get("node_history", []) + ["persist"]
    return {"node_history": history}
