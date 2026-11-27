from __future__ import annotations

import hashlib
from typing import TypeVar

from pydantic import BaseModel

from ai.llm.base import LLMProvider
from models.assignment import Category, ClassificationResult
from models.evaluation import (
    DeterministicFinding,
    EvaluationResult,
    SectionEvaluation,
    SectionScore,
)
from models.report import SectionDraft

T = TypeVar("T", bound=BaseModel)


class MockProvider(LLMProvider):
    """
    Deterministic LLM provider for tests and offline operation without API keys.
    """

    def __init__(self, force_pass: bool = True):
        self.force_pass = force_pass

    def generate_structured(
        self,
        schema: type[T],
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
    ) -> T:
        if schema == ClassificationResult:
            if "lab" in user_prompt.lower() or "experiment" in user_prompt.lower():
                return ClassificationResult(
                    category=Category.INITIAL_LAB,
                    confidence=0.95,
                    rationale="Detected laboratory apparatus and experimental procedure keywords.",
                    method="mock",
                )  # type: ignore
            return ClassificationResult(
                category=Category.ASSIGNMENT,
                confidence=0.92,
                rationale="Detected standard assignment topic and theoretical questions.",
                method="mock",
            )  # type: ignore

        if schema == SectionDraft:
            heading = "Section"
            for line in user_prompt.split("\n"):
                if "Current Section to Generate:" in line or "section '" in line:
                    heading = line.split(":")[-1].replace("'", "").strip()
                    break

            sample_body = (
                f"### {heading}\n\n"
                f"This section discusses the core academic principles and analysis regarding {heading.lower()}. "
                f"The experimental methodology followed established standards and guidelines [1]. "
                f"Empirical observations align with theoretical predictions within acceptable margins of error.\n\n"
                f"Further investigation into the results confirms that all criteria specified in the academic requirements have been met."
            )
            return SectionDraft(
                heading=heading,
                body_markdown=sample_body,
                citations=["[1]"],
                word_count=len(sample_body.split()),
            )  # type: ignore

        if schema == EvaluationResult:
            passed = self.force_pass
            findings = [
                DeterministicFinding(
                    check_name="mock_check",
                    passed=passed,
                    message="All checks passed in mock evaluation" if passed else "Section failed mock check",
                )
            ]
            sec_eval = SectionEvaluation(
                section_heading="Overview",
                scores=[SectionScore(criterion_id="clarity", score=0.95 if passed else 0.4, comments="Good")],
                passed=passed,
                issues=[] if passed else ["Needs more detailed derivations"],
                suggestions=[],
            )
            return EvaluationResult(
                overall_passed=passed,
                deterministic_passed=passed,
                semantic_passed=passed,
                overall_score=0.95 if passed else 0.45,
                deterministic_findings=findings,
                section_evaluations=[sec_eval],
                failed_sections=[] if passed else ["Overview"],
                general_feedback="Mock evaluation complete.",
            )  # type: ignore

        # Default fallback for other models: construct empty instance
        return schema.model_validate({})

    def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.4,
    ) -> str:
        return f"Mock response for prompt: {user_prompt[:50]}..."

    def embed(self, texts: list[str], input_type: str = "passage") -> list[list[float]]:
        # Deterministic pseudo-embedding of 768 dimensions based on SHA256
        embeddings = []
        for text in texts:
            h = hashlib.sha256(text.encode("utf-8")).digest()
            vec = [(float(b) / 255.0) - 0.5 for b in h]
            while len(vec) < 768:
                vec.extend(vec[: min(768 - len(vec), len(vec))])
            embeddings.append(vec[:768])
        return embeddings
