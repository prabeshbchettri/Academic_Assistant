from __future__ import annotations

import logging
import re
from pathlib import Path

from jinja2 import Template

from ai.llm.base import LLMProvider
from configs.schema import CategoryConfig
from models.evaluation import (
    DeterministicFinding,
    EvaluationResult,
    EvaluationStatus,
    SectionEvaluation,
)
from models.report import ReportContent

logger = logging.getLogger(__name__)

CITATION_PATTERN = re.compile(r"\[(\d+)\]")

BANNED_PHRASES = [
    r"as an ai language model",
    r"i cannot fulfill",
    r"i am sorry, but",
    r"as an ai,",
]


class Evaluator:
    def __init__(self, llm: LLMProvider):
        self.llm = llm

    def run_deterministic_checks(
        self,
        config: CategoryConfig,
        report: ReportContent,
    ) -> tuple[bool, list[DeterministicFinding]]:
        findings = []
        all_passed = True

        # Check required sections present
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

        # Check section word limits
        for sec in report.sections:
            sec_key = sec.heading.lower().replace(" ", "_")
            limits = config.word_limits.sections.get(sec_key)
            if limits:
                if sec.word_count < limits.min:
                    findings.append(
                        DeterministicFinding(
                            check_name="word_count_min",
                            passed=False,
                            message=f"Section '{sec.heading}' word count ({sec.word_count}) below min limit ({limits.min}).",
                            section=sec.heading,
                        )
                    )
                    all_passed = False
                elif sec.word_count > limits.max:
                    findings.append(
                        DeterministicFinding(
                            check_name="word_count_max",
                            passed=False,
                            message=f"Section '{sec.heading}' word count ({sec.word_count}) exceeds max limit ({limits.max}).",
                            section=sec.heading,
                        )
                    )
                    all_passed = False

        # Check banned LLM hallucination markers
        for sec in report.sections:
            for pattern in BANNED_PHRASES:
                if re.search(pattern, sec.body_markdown, re.IGNORECASE):
                    findings.append(
                        DeterministicFinding(
                            check_name="banned_phrases",
                            passed=False,
                            message=f"Section '{sec.heading}' contains disallowed AI disclaimer marker: '{pattern}'.",
                            section=sec.heading,
                        )
                    )
                    all_passed = False

        # Check citation integrity: every citation must map to a supplied reference,
        # whether it appears in the structured citation list or in the body text.
        ref_keys = {r.key.strip() for r in report.references if r.key.strip()}
        for sec in report.sections:
            cited = {c.strip() for c in sec.citations if c.strip()}
            cited.update(f"[{number}]" for number in CITATION_PATTERN.findall(sec.body_markdown))
            for cit in sorted(cited):
                if cit not in ref_keys and not any(r in cit for r in ref_keys):
                    findings.append(
                        DeterministicFinding(
                            check_name="citation_validity",
                            passed=False,
                            message=(
                                f"Section '{sec.heading}' cites '{cit}' which is not in the "
                                "supplied references table."
                            ),
                            section=sec.heading,
                        )
                    )
                    all_passed = False

        # Check that the category's reference requirement is actually satisfied.
        # Missing references are reported, never manufactured.
        if config.references.required:
            available = len(
                {(r.key or f"{r.title}|{r.authors}").strip().lower() for r in report.references}
            )
            if available < config.references.min_count:
                findings.append(
                    DeterministicFinding(
                        check_name="references_min_count",
                        passed=False,
                        message=(
                            f"Only {available} supplied reference(s) but this category requires "
                            f"{config.references.min_count}; references must not be invented to "
                            "satisfy this requirement."
                        ),
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

    def evaluate_semantic(
        self,
        config: CategoryConfig,
        report: ReportContent,
    ) -> EvaluationResult:
        det_passed, findings = self.run_deterministic_checks(config, report)

        if not report.sections:
            # An empty report is a genuine quality failure, never an automatic pass.
            logger.warning("Report contains no sections; evaluation cannot pass.")
            return EvaluationResult(
                status=EvaluationStatus.FAILED,
                overall_passed=False,
                deterministic_passed=det_passed,
                semantic_passed=False,
                overall_score=0.0,
                deterministic_findings=findings,
                section_evaluations=[],
                failed_sections=["(entire report)"],
                general_feedback="Report contains no sections, so it cannot pass evaluation.",
            )

        root_dir = Path(__file__).resolve().parent.parent
        eval_prompt_path = root_dir / config.prompts.evaluation
        eval_template = eval_prompt_path.read_text(encoding="utf-8") if eval_prompt_path.exists() else "Evaluate: {{ body_markdown }}"

        rubric_text = "\n".join(f"- {r.id} (weight {r.weight}): {r.description}" for r in config.rubric)

        section_evaluations: list[SectionEvaluation] = []
        failed_sections: list[str] = []
        evaluation_errors: list[str] = []

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
            )

            try:
                res = self.llm.generate_structured(EvaluationResult, "You are an evaluator.", prompt)
            except Exception as exc:
                # Never fabricate a pass: record the failure and report it as inconclusive.
                logger.exception(
                    "Provider failed while evaluating section '%s'; evaluation cannot be trusted.",
                    sec.heading,
                )
                evaluation_errors.append(f"{sec.heading}: {type(exc).__name__}")
                continue

            if not res.section_evaluations:
                logger.warning(
                    "Evaluator returned no section evaluation for '%s'; "
                    "treating the response as incomplete.",
                    sec.heading,
                )
                evaluation_errors.append(f"{sec.heading}: evaluator returned no section evaluation")
                continue

            sec_eval = res.section_evaluations[0]
            sec_eval.section_heading = sec.heading
            section_evaluations.append(sec_eval)
            if not sec_eval.passed:
                failed_sections.append(sec.heading)

        # Also add any deterministic failures to failed_sections
        for f in findings:
            if not f.passed and f.section and f.section not in failed_sections:
                failed_sections.append(f.section)

        if evaluation_errors:
            # A partially evaluated report is never a passing report.
            logger.error("Evaluation incomplete: %s", "; ".join(evaluation_errors))
            return EvaluationResult(
                status=EvaluationStatus.INCONCLUSIVE,
                overall_passed=False,
                deterministic_passed=det_passed,
                semantic_passed=False,
                overall_score=0.0,
                deterministic_findings=findings,
                section_evaluations=section_evaluations,
                failed_sections=failed_sections,
                general_feedback=(
                    "Automated evaluation could not be completed, so the report was not accepted. "
                    f"Failed checks: {'; '.join(evaluation_errors)}"
                ),
            )

        semantic_passed = len(failed_sections) == 0
        overall_passed = det_passed and semantic_passed

        return EvaluationResult(
            status=EvaluationStatus.PASSED if overall_passed else EvaluationStatus.FAILED,
            overall_passed=overall_passed,
            deterministic_passed=det_passed,
            semantic_passed=semantic_passed,
            overall_score=0.92 if overall_passed else 0.55,
            deterministic_findings=findings,
            section_evaluations=section_evaluations,
            failed_sections=failed_sections,
            general_feedback="Evaluation passed successfully." if overall_passed else f"Issues detected in: {', '.join(failed_sections)}",
        )
