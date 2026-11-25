from __future__ import annotations

import logging
import re
from pathlib import Path

from jinja2 import Template

from ai.llm.base import LLMProvider
from ai.security import wrap_untrusted_data
from configs.schema import CategoryConfig
from models.assignment import NormalizedInput
from models.evaluation import (
    DeterministicFinding,
    EvaluationResult,
    SectionEvaluation,
    SectionScore,
)
from models.report import ReportContent

logger = logging.getLogger(__name__)

BANNED_PHRASES = [
    r"as an ai language model",
    r"i cannot fulfill",
    r"i am sorry, but",
    r"as an ai,",
]

_MISSING_RE = re.compile(r"\[\[MISSING:\s*([^\]]+)\]\]")


def format_section_feedback(eval_result: EvaluationResult, section_heading: str) -> str:
    """Extracts actionable deterministic + rubric critique for a specific section."""
    notes: list[str] = []
    for finding in eval_result.deterministic_findings:
        if (
            not finding.passed
            and finding.section
            and finding.section.lower() == section_heading.lower()
        ):
            notes.append(f"- Constraint violation ({finding.check_name}): {finding.message}")

    for sec_eval in eval_result.section_evaluations:
        if sec_eval.section_heading.lower() == section_heading.lower():
            for issue in sec_eval.issues:
                notes.append(f"- Issue: {issue}")
            for suggestion in sec_eval.suggestions:
                notes.append(f"- Suggestion: {suggestion}")
            for score in sec_eval.scores:
                if score.score < 0.7:
                    notes.append(
                        f"- Low score on '{score.criterion_id}' ({score.score:.2f}): "
                        f"{score.comments}"
                    )

    return "\n".join(notes)


class Evaluator:
    def __init__(self, llm: LLMProvider):
        self.llm = llm

    def run_deterministic_checks(
        self,
        config: CategoryConfig,
        report: ReportContent,
    ) -> tuple[bool, list[DeterministicFinding]]:
        findings: list[DeterministicFinding] = []
        all_passed = True

        existing_headings = {s.heading.lower().replace(" ", "_") for s in report.sections}
        for req in config.required_sections:
            if req in ("references", "bibliography"):
                continue
            if req not in existing_headings:
                all_passed = False
                findings.append(
                    DeterministicFinding(
                        check_name="required_section_present",
                        passed=False,
                        message=f"Missing required section: {req}",
                        section=req,
                    )
                )

        for sec in report.sections:
            sec_key = sec.heading.lower().replace(" ", "_")
            limits = config.word_limits.sections.get(sec_key)
            if limits:
                if sec.word_count < limits.min:
                    findings.append(
                        DeterministicFinding(
                            check_name="word_count_min",
                            passed=False,
                            message=(
                                f"Section '{sec.heading}' word count ({sec.word_count}) "
                                f"below min limit ({limits.min})."
                            ),
                            section=sec.heading,
                        )
                    )
                    all_passed = False
                elif sec.word_count > limits.max:
                    findings.append(
                        DeterministicFinding(
                            check_name="word_count_max",
                            passed=False,
                            message=(
                                f"Section '{sec.heading}' word count ({sec.word_count}) "
                                f"exceeds max limit ({limits.max})."
                            ),
                            section=sec.heading,
                        )
                    )
                    all_passed = False

            for pattern in BANNED_PHRASES:
                if re.search(pattern, sec.body_markdown, re.IGNORECASE):
                    findings.append(
                        DeterministicFinding(
                            check_name="banned_phrases",
                            passed=False,
                            message=(
                                f"Section '{sec.heading}' contains disallowed AI disclaimer "
                                f"marker: '{pattern}'."
                            ),
                            section=sec.heading,
                        )
                    )
                    all_passed = False

            missing_matches = _MISSING_RE.findall(sec.body_markdown)
            if missing_matches:
                # Track unresolved placeholders as advisory findings without forcing LLM retries
                fields = ", ".join(m.strip() for m in missing_matches[:4])
                findings.append(
                    DeterministicFinding(
                        check_name="missing_data_placeholders",
                        passed=True,
                        message=(
                            f"Section '{sec.heading}' contains {len(missing_matches)} student "
                            f"placeholder(s) to complete: {fields}."
                        ),
                        section=sec.heading,
                    )
                )

        ref_keys = {r.key.strip() for r in report.references}
        for sec in report.sections:
            for cit in sec.citations:
                if cit.strip() not in ref_keys and not any(r in cit for r in ref_keys):
                    findings.append(
                        DeterministicFinding(
                            check_name="citation_validity",
                            passed=False,
                            message=(
                                f"Section '{sec.heading}' cites '{cit}' which is not "
                                "in references table."
                            ),
                            section=sec.heading,
                        )
                    )
                    all_passed = False

        if config.references.required and len(report.references) < 1:
            findings.append(
                DeterministicFinding(
                    check_name="references_present",
                    passed=False,
                    message="Report has no bibliographic or assignment source references.",
                )
            )
            all_passed = False

        if all_passed:
            findings.append(
                DeterministicFinding(
                    check_name="deterministic_all",
                    passed=True,
                    message="All deterministic structure, word count, and citation checks passed.",
                )
            )

        return all_passed, findings

    def _compute_weighted_score(
        self,
        config: CategoryConfig,
        section_evaluations: list[SectionEvaluation],
        findings: list[DeterministicFinding],
    ) -> float:
        weights = {item.id.lower(): item.weight for item in config.rubric}
        if not section_evaluations:
            return 0.0

        section_totals: list[float] = []
        for sec_eval in section_evaluations:
            if not sec_eval.scores:
                section_totals.append(0.85 if sec_eval.passed else 0.45)
                continue
            weighted_sum = 0.0
            weight_acc = 0.0
            for s in sec_eval.scores:
                w = weights.get(s.criterion_id.lower(), 1.0 / max(1, len(config.rubric)))
                weighted_sum += max(0.0, min(1.0, s.score)) * w
                weight_acc += w
            sec_score = (weighted_sum / weight_acc) if weight_acc > 0 else 0.0
            section_totals.append(sec_score)

        base_score = sum(section_totals) / len(section_totals)
        det_failures = sum(1 for f in findings if not f.passed)
        penalty = min(0.35, det_failures * 0.07)
        return round(max(0.0, min(1.0, base_score - penalty)), 3)

    def evaluate_semantic(
        self,
        config: CategoryConfig,
        report: ReportContent,
        normalized: NormalizedInput | None = None,
    ) -> EvaluationResult:
        det_passed, findings = self.run_deterministic_checks(config, report)

        root_dir = Path(__file__).resolve().parent.parent
        eval_prompt_path = root_dir / config.prompts.evaluation
        eval_template = (
            eval_prompt_path.read_text(encoding="utf-8")
            if eval_prompt_path.exists()
            else "Evaluate: {{ body_markdown }}"
        )

        rubric_text = "\n".join(
            f"- {r.id} (weight {r.weight}): {r.description}" for r in config.rubric
        )
        assignment_context = ""
        if normalized is not None:
            wrapped, _ = wrap_untrusted_data(normalized.cleaned_text[:2500])
            assignment_context = wrapped

        section_evaluations: list[SectionEvaluation] = []
        failed_sections: list[str] = []

        for sec in report.sections:
            limits = config.word_limits.sections.get(sec.heading.lower().replace(" ", "_"))
            min_w = limits.min if limits else 100
            max_w = limits.max if limits else 600

            template = Template(eval_template)
            prompt = template.render(
                section_heading=sec.heading,
                body_markdown=sec.body_markdown,
                rubric_text=rubric_text,
                min_words=min_w,
                max_words=max_w,
                word_count=sec.word_count,
                assignment_context=assignment_context,
            )

            try:
                sec_eval = self.llm.generate_structured(
                    SectionEvaluation,
                    (
                        "You are a strict academic evaluator. Score each rubric criterion "
                        "from 0.0 to 1.0 using exact criterion_id keys and return a "
                        "SectionEvaluation JSON object."
                    ),
                    prompt,
                )
                sec_eval.section_heading = sec.heading
                section_evaluations.append(sec_eval)
                if not sec_eval.passed:
                    failed_sections.append(sec.heading)
            except Exception as exc:
                logger.warning(
                    "LLM semantic evaluation failed for '%s': %s; "
                    "falling back to deterministic checks.",
                    sec.heading,
                    exc,
                )
                sec_det_failed = any(
                    not f.passed and f.section and f.section.lower() == sec.heading.lower()
                    for f in findings
                )
                fallback_score = 0.45 if sec_det_failed else 0.78
                scores = [
                    SectionScore(
                        criterion_id=r.id,
                        score=fallback_score,
                        comments="Deterministic fallback score (LLM judge unavailable).",
                    )
                    for r in config.rubric
                ]
                findings.append(
                    DeterministicFinding(
                        check_name="semantic_eval_degraded",
                        passed=True,
                        message=(
                            f"LLM judge unavailable for '{sec.heading}'; "
                            f"used deterministic verification."
                        ),
                        section=sec.heading,
                    )
                )
                section_evaluations.append(
                    SectionEvaluation(
                        section_heading=sec.heading,
                        scores=scores,
                        passed=not sec_det_failed,
                        issues=(
                            ["Failed deterministic verification while LLM judge was unavailable."]
                            if sec_det_failed
                            else []
                        ),
                    )
                )
                if sec_det_failed:
                    failed_sections.append(sec.heading)

        for f in findings:
            if not f.passed and f.section and f.section not in failed_sections:
                failed_sections.append(f.section)

        semantic_passed = len(failed_sections) == 0
        overall_passed = det_passed and semantic_passed
        overall_score = self._compute_weighted_score(config, section_evaluations, findings)

        return EvaluationResult(
            overall_passed=overall_passed,
            deterministic_passed=det_passed,
            semantic_passed=semantic_passed,
            overall_score=overall_score,
            deterministic_findings=findings,
            section_evaluations=section_evaluations,
            failed_sections=failed_sections,
            general_feedback=(
                f"All checks passed (weighted score: {overall_score:.2f})."
                if overall_passed
                else f"Issues detected in: {', '.join(failed_sections)} "
                f"(weighted score: {overall_score:.2f})."
            ),
        )
