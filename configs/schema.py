from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class RangeLimit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    min: int = Field(ge=0)
    max: int = Field(gt=0)

    @model_validator(mode="after")
    def check_min_max(self) -> RangeLimit:
        if self.min > self.max:
            raise ValueError(f"min ({self.min}) cannot be greater than max ({self.max})")
        return self


class WordLimits(BaseModel):
    model_config = ConfigDict(extra="forbid")
    total: RangeLimit
    sections: dict[str, RangeLimit] = Field(default_factory=dict)


class MarginConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    top: float = 1.0
    bottom: float = 1.0
    left: float = 1.0
    right: float = 1.0


class FormattingConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    font: str = "Liberation Serif"
    font_size: int = 11
    line_spacing: float = 1.15
    margins_inches: MarginConfig = Field(default_factory=MarginConfig)
    citation_style: str = "IEEE"
    heading_numbering: bool = True


class PromptsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    system: str
    generation: str
    evaluation: str


class RubricItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    weight: float = Field(ge=0.0, le=1.0)
    description: str


class RagCategoryConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool = False
    collections: list[str] = Field(default_factory=list)


class ReferencesConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    required: bool = True
    min_count: int = 1


class CategoryConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    category: str
    display_name: str
    required_sections: list[str]
    word_limits: WordLimits
    formatting: FormattingConfig = Field(default_factory=FormattingConfig)
    prompts: PromptsConfig
    rubric: list[RubricItem]
    rag: RagCategoryConfig = Field(default_factory=RagCategoryConfig)
    references: ReferencesConfig = Field(default_factory=ReferencesConfig)

    @field_validator("required_sections")
    @classmethod
    def validate_required_sections(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("required_sections must not be empty")
        return v

    @model_validator(mode="after")
    def validate_rubric_weights(self) -> CategoryConfig:
        total_weight = sum(item.weight for item in self.rubric)
        if abs(total_weight - 1.0) > 1e-4:
            raise ValueError(f"Rubric weights must sum to 1.0, got {total_weight}")

        # Check that required sections each have word limits or fall back to section defaults
        for sec in self.required_sections:
            if sec not in self.word_limits.sections:
                # Provide a sensible default section limit if not explicitly defined
                self.word_limits.sections[sec] = RangeLimit(min=50, max=1000)

        return self


_CONFIG_CACHE: dict[str, CategoryConfig] = {}


def load_category_config(category: str, base_dir: Path | None = None) -> CategoryConfig:
    if category in _CONFIG_CACHE:
        return _CONFIG_CACHE[category]

    if base_dir is None:
        base_dir = Path(__file__).resolve().parent

    config_path = base_dir / f"{category}.yaml"
    if not config_path.exists():
        raise FileNotFoundError(
            f"Configuration file for category '{category}' not found at {config_path}"
        )

    raw_yaml = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config = CategoryConfig.model_validate(raw_yaml)
    _CONFIG_CACHE[category] = config
    return config


def preload_all_configs(base_dir: Path | None = None) -> dict[str, CategoryConfig]:
    categories = ["assignment", "initial_lab", "final_lab"]
    configs = {}
    for cat in categories:
        configs[cat] = load_category_config(cat, base_dir)
    return configs
