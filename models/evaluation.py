from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, model_validator


class DecisionType(str, Enum):
    APPROVE = "approve"
    EDIT = "edit"
    REGENERATE = "regenerate"
    REJECT = "reject"


class DeterministicFinding(BaseModel):
    check_name: str
    passed: bool
    message: str
    section: str | None = None


class SectionScore(BaseModel):
    criterion_id: str
    score: float = Field(ge=0.0, le=1.0)
    comments: str


class SectionEvaluation(BaseModel):
    section_heading: str
    scores: list[SectionScore] = Field(default_factory=list)
    passed: bool = True
    issues: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


class EvaluationStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    INCONCLUSIVE = "inconclusive"


class EvaluationResult(BaseModel):
    # Defaults to INCONCLUSIVE so a result that omits its status can never be read as a pass.
    status: EvaluationStatus = EvaluationStatus.INCONCLUSIVE
    overall_passed: bool
    deterministic_passed: bool
    semantic_passed: bool
    overall_score: float = Field(default=1.0, ge=0.0, le=1.0)
    deterministic_findings: list[DeterministicFinding] = Field(default_factory=list)
    section_evaluations: list[SectionEvaluation] = Field(default_factory=list)
    failed_sections: list[str] = Field(default_factory=list)
    general_feedback: str = ""

    @model_validator(mode="after")
    def validate_pass_status(self) -> EvaluationResult:
        if self.status == EvaluationStatus.PASSED and not self.overall_passed:
            raise ValueError("status='passed' requires overall_passed=True")
        if self.overall_passed and (
            self.status != EvaluationStatus.PASSED
            or not self.deterministic_passed
            or not self.semantic_passed
        ):
            raise ValueError(
                "overall_passed=True requires status='passed', deterministic_passed=True "
                "and semantic_passed=True"
            )
        return self


class HumanDecision(BaseModel):
    decision: DecisionType
    feedback: str = ""
    edited_sections: dict[str, str] = Field(default_factory=dict)
    regenerate_sections: list[str] = Field(default_factory=list)
    approved_at: str | None = None
