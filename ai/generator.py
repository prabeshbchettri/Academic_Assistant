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
from models.report import (
    Citation,
    FrontPage,
    ReferenceProvenance,
    ReportContent,
    SectionDraft,
)

logger = logging.getLogger(__name__)


def _format_user_provided_data(raw: Any) -> str:
    """Renders the workflow's user_provided_data contract as plain prompt text.

    The state contract stores ``{"details": <text>}``, but any non-empty mapping
    entries are rendered so no answer is silently dropped. Returns an empty
    string when nothing was supplied.
    """
    if not raw:
        return ""
    if isinstance(raw, str):
        return raw.strip()
    if not isinstance(raw, dict):
        return str(raw).strip()

    parts: list[str] = []
    for key, value in raw.items():
        if value is None:
            continue
        text = str(value).strip()
        if not text:
            continue
        if key == "details":
            parts.append(text)
        else:
            parts.append(f"{str(key).replace('_', ' ').title()}: {text}")
    return "\n".join(parts)


class SectionGenerator:
    def __init__(self, llm: LLMProvider):
        self.llm = llm

    @staticmethod
    def _format_reference_for_prompt(reference: Citation) -> str:
        """Renders a supplied citation for the generation prompt without adding data."""
        parts = [
            part
            for part in (
                reference.authors,
                f'"{reference.title}"' if reference.title.strip() else "",
                reference.venue,
                reference.year,
            )
            if part.strip()
        ]
        return f"{reference.key} {', '.join(parts)}.".strip()

    @staticmethod
    def _prepare_references(references: list[Citation]) -> list[Citation]:
        """Returns the bibliography entries that may be rendered.

        Only caller-supplied references are kept: LLM-suggested entries are never
        promoted to bibliography entries, and no placeholder or example reference
        is synthesized when the list is empty.
        """
        prepared: list[Citation] = []
        seen: set[str] = set()
        for reference in references:
            if reference.provenance == ReferenceProvenance.LLM_SUGGESTION:
                logger.warning(
                    "Dropping LLM-suggested reference '%s'; it is not a verified source.",
                    reference.key or reference.title,
                )
                continue
            identity = (
                reference.key or f"{reference.title}|{reference.authors}"
            ).strip().lower()
            if identity in seen:
                logger.warning(
                    "Dropping duplicate reference '%s'.",
                    reference.key or reference.title,
                )
                continue
            seen.add(identity)
            prepared.append(reference)
        return prepared

    def generate_section(
        self,
        config: CategoryConfig,
        normalized: NormalizedInput,
        section_name: str,
        prior_sections: list[SectionDraft],
        calculated_data: str = "",
        references_context: str = "",
        user_provided_data: dict[str, Any] | None = None,
        feedback: str = "",
    ) -> SectionDraft:
        # Load prompt templates
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

        limits = config.word_limits.sections.get(section_name)
        min_words = limits.min if limits else 100
        max_words = limits.max if limits else 500

        prior_summary = "\n".join(f"- {s.heading}: {s.word_count} words" for s in prior_sections)
        wrapped_assignment, _ = wrap_untrusted_data(normalized.cleaned_text)
        user_data_text = _format_user_provided_data(user_provided_data)
        wrapped_user_data = wrap_untrusted_data(user_data_text)[0] if user_data_text else ""
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
            user_provided_data=wrapped_user_data,
            prior_sections_summary=prior_summary,
            feedback=feedback,
            document_type=document_type,
            format_notes=format_notes,
            assignment_notes=assignment_notes,
            revision_feedback=revision_feedback,
        )

        draft = self.llm.generate_structured(SectionDraft, system_prompt, user_prompt)
        # Ensure word count is accurately measured
        draft.word_count = len(draft.body_markdown.split())
        draft.heading = section_name.replace("_", " ").title()

        # Detect missing placeholders
        placeholders = re.findall(r"\[\[MISSING:[^\]]+\]\]", draft.body_markdown)
        draft.missing_placeholders = placeholders

        return draft

    def generate_full_report(
        self,
        config: CategoryConfig,
        normalized: NormalizedInput,
        references: list[Citation] | None = None,
        retrieved_chunks: list[str] | None = None,
        user_provided_data: dict[str, Any] | None = None,
    ) -> ReportContent:
        # Never invent bibliography entries: an empty list stays empty.
        report_references = self._prepare_references(references or [])

        formulas = extract_and_evaluate_formulas(normalized.cleaned_text)
        calc_summary = "\n".join(
            f"- {f['variable']} = {f['expression']} => {f['value']}" for f in formulas
        )
        ref_context_parts = list(retrieved_chunks or [])
        ref_context_parts.extend(
            self._format_reference_for_prompt(ref) for ref in report_references
        )
        ref_context = "\n".join(part for part in ref_context_parts if part.strip())

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
                user_provided_data=user_provided_data,
            )
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
                logo_path=doc_prefs.get("logo_path") or str(
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
            references=report_references,
            front_page=front_page,
            document_type=document_type,
            include_toc=bool(doc_prefs.get("include_toc", True)),
            metadata={
                "document_preferences": doc_prefs,
                "student_profile": student,
            },
        )
