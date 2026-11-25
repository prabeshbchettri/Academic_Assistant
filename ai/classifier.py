from __future__ import annotations

import re

from ai.llm.base import LLMProvider
from ai.security import wrap_untrusted_data
from models.assignment import Category, ClassificationResult, NormalizedInput

LAB_KEYWORDS = [
    "apparatus",
    "procedure",
    "observation",
    "observations",
    "trials",
    "equipment",
    "experiment",
    "measurement",
    "measurements",
    "lab report",
    "lab sheet",
    "objective",
]

FINAL_LAB_KEYWORDS = [
    "final lab",
    "comprehensive lab",
    "error analysis",
    "error propagation",
    "theoretical derivation",
    "methodology",
    "project report",
]

ASSIGNMENT_KEYWORDS = [
    "assignment",
    "homework",
    "questions",
    "problem set",
    "essay",
    "review",
    "exercises",
    "derive",
    "solve",
]


class Classifier:
    def __init__(self, llm: LLMProvider | None = None):
        self.llm = llm

    def classify_by_rules(self, text: str) -> tuple[Category | None, float, str]:
        lower = text.lower()

        final_score = sum(
            1 for kw in FINAL_LAB_KEYWORDS if re.search(r"\b" + re.escape(kw) + r"\b", lower)
        )
        lab_score = sum(
            1 for kw in LAB_KEYWORDS if re.search(r"\b" + re.escape(kw) + r"\b", lower)
        )
        assign_score = sum(
            1 for kw in ASSIGNMENT_KEYWORDS if re.search(r"\b" + re.escape(kw) + r"\b", lower)
        )

        if final_score >= 2 or ("final" in lower and lab_score >= 2):
            return (
                Category.FINAL_LAB,
                0.90,
                f"Matched {final_score} final lab indicators (error analysis, project/final lab).",
            )
        if lab_score >= 2 or "experiment" in lower or "lab report" in lower or "lab sheet" in lower:
            return (
                Category.INITIAL_LAB,
                0.88,
                f"Matched {lab_score} laboratory keywords (apparatus, procedure, observations).",
            )
        if assign_score >= 1 or "question" in lower or "problem" in lower:
            return (
                Category.ASSIGNMENT,
                0.85,
                "Matched assignment keywords (questions, homework, problem set).",
            )

        return None, 0.0, "No definitive rule matches."

    def classify(
        self,
        normalized: NormalizedInput,
        manual_category: Category | None = None,
    ) -> ClassificationResult:
        if manual_category:
            return ClassificationResult(
                category=manual_category,
                confidence=1.0,
                rationale="Explicit user manual selection.",
                method="manual",
            )

        combined = f"{normalized.title}\n{normalized.cleaned_text}".strip()
        rule_cat, rule_conf, rule_rationale = self.classify_by_rules(combined)
        if rule_cat is not None and rule_conf >= 0.85:
            return ClassificationResult(
                category=rule_cat,
                confidence=rule_conf,
                rationale=rule_rationale,
                method="rule",
            )

        if self.llm is not None:
            wrapped_text, _ = wrap_untrusted_data(normalized.cleaned_text[:3000])
            system_prompt = (
                "You are an academic classifier. Classify the student assignment into one of: "
                "'assignment', 'initial_lab', 'final_lab'. "
                "Output valid JSON conforming to the schema."
            )
            user_prompt = f"Title: {normalized.title}\nAssignment Text:\n{wrapped_text}"
            try:
                result = self.llm.generate_structured(
                    ClassificationResult, system_prompt, user_prompt
                )
                result.method = "llm"
                return result
            except Exception:
                pass

        return ClassificationResult(
            category=Category.ASSIGNMENT,
            confidence=0.70,
            rationale="Defaulted to assignment due to ambiguous indicators.",
            method="rule",
        )
