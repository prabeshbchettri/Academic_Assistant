from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from jinja2 import Template

from ai.calculations import extract_and_evaluate_formulas
from ai.llm.base import LLMProvider
from ai.security import wrap_untrusted_data
from configs.schema import CategoryConfig
from models.assignment import NormalizedInput
from models.report import Citation, FrontPage, ReportContent, SectionDraft

logger = logging.getLogger(__name__)


def build_grounded_references(
    normalized: NormalizedInput,
    retrieved_sources: list[dict[str, Any]] | None = None,
    explicit_references: list[Citation] | None = None,
) -> list[Citation]:
    """
    Constructs verifiable citations strictly from explicitly supplied references,
    retrieved RAG course documents, or the source assignment sheet itself.
    Never fabricates fictional academic authors or publications.
    """
    if explicit_references:
        return explicit_references

    citations: list[Citation] = []
    seen_sources: set[str] = set()
    year = str(datetime.now().year)

    for src in retrieved_sources or []:
        name = str(src.get("source") or "").strip()
        if not name or name in seen_sources:
            continue
        seen_sources.add(name)
        idx = len(citations) + 1
        citations.append(
            Citation(
                key=f"[{idx}]",
                authors=normalized.course_name or "Course Reference",
                title=name,
                year=year,
                venue="Indexed Course Material (RAG)",
            )
        )

    # Always allow citing attached/course assignment instructions cleanly
    course_label = normalized.course_name or "Academic Coursework"
    if normalized.attachments:
        for att in normalized.attachments:
            att_name = Path(att).name
            if att_name not in seen_sources:
                seen_sources.add(att_name)
                idx = len(citations) + 1
                citations.append(
                    Citation(
                        key=f"[{idx}]",
                        authors=course_label,
                        title=att_name,
                        year=year,
                        venue="Course Assignment Material",
                    )
                )

    if not citations:
        citations.append(
            Citation(
                key="[1]",
                authors=course_label,
                title=normalized.title or "Course Assignment Specification",
                year=year,
                venue="Course Assignment Brief",
            )
        )

    return citations


class SectionGenerator:
    def __init__(self, llm: LLMProvider):
        self.llm = llm

    def generate_section(
        self,
        config: CategoryConfig,
        normalized: NormalizedInput,
        section_name: str,
        prior_sections: list[SectionDraft],
        calculated_data: str = "",
        references_context: str = "",
        feedback: str = "",
        available_references: str = "",
    ) -> SectionDraft:
        root_dir = Path(__file__).resolve().parent.parent
        sys_prompt_path = root_dir / config.prompts.system
        gen_prompt_path = root_dir / config.prompts.generation

        system_prompt = (
            sys_prompt_path.read_text(encoding="utf-8")
            if sys_prompt_path.exists()
            else "You are an academic assistant."
        )
        generation_template = (
            gen_prompt_path.read_text(encoding="utf-8")
            if gen_prompt_path.exists()
            else "{{ assignment_text }}"
        )

        section_key = section_name.lower().replace(" ", "_")
        limits = config.word_limits.sections.get(section_key)
        min_words = limits.min if limits else 100
        max_words = limits.max if limits else 500

        prior_summary = "\n".join(
            f"- {s.heading}: {s.word_count} words" for s in prior_sections
        )
        wrapped_assignment, _ = wrap_untrusted_data(normalized.cleaned_text)
        doc_prefs = normalized.metadata.get("document_preferences", {}) or {}
        format_notes = doc_prefs.get("format_notes", "") or ""
        assignment_notes = normalized.metadata.get("assignment_notes", "") or ""
        revision_feedback = normalized.metadata.get("revision_feedback", "") or ""
        document_type = doc_prefs.get("document_type") or config.display_name

        template = Template(generation_template)
        user_prompt = template.render(
            title=normalized.title,
            course=normalized.course_name or "Academic Coursework",
            assignment_text=wrapped_assignment,
            section_heading=section_name.replace("_", " ").title(),
            min_words=min_words,
            max_words=max_words,
            calculated_data=calculated_data,
            references_context=references_context,
            available_references=available_references,
            prior_sections_summary=prior_summary,
            feedback=feedback,
            document_type=document_type,
            format_notes=format_notes,
            assignment_notes=assignment_notes,
            revision_feedback=revision_feedback,
        )

        draft = self.llm.generate_structured(SectionDraft, system_prompt, user_prompt)
        draft.word_count = len(draft.body_markdown.split())
        draft.heading = section_name.replace("_", " ").title()

        placeholders = re.findall(r"\[\[MISSING:[^\]]+\]\]", draft.body_markdown)
        draft.missing_placeholders = placeholders

        return draft

    def generate_full_report(
        self,
        config: CategoryConfig,
        normalized: NormalizedInput,
        references: list[Citation] | None = None,
        retrieved_chunks: list[str] | None = None,
        retrieved_sources: list[dict[str, Any]] | None = None,
    ) -> ReportContent:
        formulas = extract_and_evaluate_formulas(normalized.cleaned_text)
        calc_summary = "\n".join(
            f"- {f['variable']} = {f['expression']} => {f['value']}" for f in formulas
        )

        if retrieved_sources:
            ref_context = "\n".join(
                f"[{idx}] ({src.get('source', 'Material')}): {src.get('text', '')}"
                for idx, src in enumerate(retrieved_sources, start=1)
            )
        else:
            ref_context = "\n".join(retrieved_chunks or [])

        grounded_refs = build_grounded_references(
            normalized,
            retrieved_sources=retrieved_sources,
            explicit_references=references,
        )
        available_refs_text = "\n".join(
            f"{r.key} {r.authors}, {r.title} ({r.venue}, {r.year})" for r in grounded_refs
        )
        valid_ref_keys = {r.key.strip() for r in grounded_refs}

        sections: list[SectionDraft] = []
        target_sections = [
            s
            for s in config.required_sections
            if s.lower() not in ("references", "bibliography")
        ]
        for idx, sec in enumerate(target_sections, 1):
            logger.info("Generating section '%s' (%d/%d)...", sec, idx, len(target_sections))
            draft = self.generate_section(
                config=config,
                normalized=normalized,
                section_name=sec,
                prior_sections=sections,
                calculated_data=calc_summary,
                references_context=ref_context,
                available_references=available_refs_text,
            )
            # Filter inline citation metadata to grounded reference keys only
            draft.citations = [c for c in draft.citations if c.strip() in valid_ref_keys]
            logger.info("Completed section '%s' (%d words).", sec, draft.word_count)
            sections.append(draft)

        abstract_sec = next(
            (s.body_markdown for s in sections if s.heading.lower() == "abstract"),
            "",
        )

        metadata = normalized.metadata or {}
        doc_prefs = metadata.get("document_preferences", {}) or {}
        student = metadata.get("student_profile", {}) or {}
        submission_date = metadata.get("submission_date") or datetime.now().strftime("%B %d, %Y")
        document_type = doc_prefs.get("document_type") or config.display_name

        front_page = None
        if doc_prefs.get("include_front_page", True):
            department_name = (
                doc_prefs.get("department")
                or student.get("department")
                or "Department of Electronics & Computer Engineering"
            )
            front_page = FrontPage(
                institution=doc_prefs.get("institution")
                or "Institute of Engineering, Pulchowk Campus",
                university=doc_prefs.get("university") or "Tribhuvan University",
                campus=doc_prefs.get("campus") or "Pulchowk Campus",
                department=department_name,
                document_type=document_type,
                title=normalized.title,
                course=normalized.course_name or "",
                submitted_by=student.get("full_name") or "Student",
                roll_number=student.get("roll_number", ""),
                group=student.get("group", ""),
                program=student.get("program", ""),
                semester=student.get("semester", ""),
                section=student.get("section", ""),
                submitted_to=metadata.get("submitted_to") or department_name,
                date=submission_date,
                logo_path=doc_prefs.get("logo_path")
                or str(
                    Path(__file__).resolve().parent.parent
                    / "document"
                    / "assets"
                    / "tu_logo.png"
                ),
            )

        return ReportContent(
            title=normalized.title,
            course=normalized.course_name or "Academic Coursework",
            author=student.get("full_name") or "Student",
            date=submission_date,
            institution=doc_prefs.get("institution")
            or "Institute of Engineering, Pulchowk Campus",
            abstract=abstract_sec,
            sections=sections,
            references=grounded_refs,
            front_page=front_page,
            document_type=document_type,
            include_toc=bool(doc_prefs.get("include_toc", True)),
            metadata={
                "document_preferences": doc_prefs,
                "student_profile": student,
            },
        )
