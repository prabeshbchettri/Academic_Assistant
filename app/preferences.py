from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

from app.settings import settings

PREFERENCES_FILENAME = "preferences.json"

DOCUMENT_TYPES: dict[str, str] = {
    "Academic Assignment": "assignment",
    "Lab Sheet": "initial_lab",
    "Initial Lab Report": "initial_lab",
    "Final Lab Report": "final_lab",
    "Project Report": "final_lab",
    "Seminar Report": "assignment",
}


class StudentProfile(BaseModel):
    full_name: str = ""
    roll_number: str = ""
    group: str = ""
    program: str = "B.E."
    department: str = ""
    semester: str = ""
    section: str = ""
    email: str = ""


class DocumentDefaults(BaseModel):
    document_type: str = "Academic Assignment"
    institution: str = "Institute of Engineering, Pulchowk Campus"
    university: str = "Tribhuvan University"
    campus: str = "Pulchowk Campus"
    department: str = ""
    include_front_page: bool = True
    include_toc: bool = True
    citation_style: str = "IEEE"
    font_family: str = "Times New Roman"
    font_size: int = 11
    line_spacing: float = 1.15
    margin_inches: float = 1.0
    logo_path: str = str(
        Path(__file__).resolve().parent.parent
        / "document"
        / "assets"
        / "tu_logo.png"
    )
    format_notes: str = ""


class AppPreferences(BaseModel):
    student: StudentProfile = Field(default_factory=StudentProfile)
    document: DocumentDefaults = Field(default_factory=DocumentDefaults)


def category_for_document_type(document_type: str) -> str:
    return DOCUMENT_TYPES.get(document_type, "assignment")


def is_profile_complete(profile: StudentProfile) -> bool:
    return bool(profile.full_name.strip() and profile.roll_number.strip())


def preferences_path() -> Path:
    return settings.storage_dir / PREFERENCES_FILENAME


def load_preferences(path: Path | None = None) -> AppPreferences:
    target = path or preferences_path()
    if not target.exists():
        return AppPreferences()
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
        return AppPreferences.model_validate(data)
    except Exception:
        return AppPreferences()


def save_preferences(prefs: AppPreferences, path: Path | None = None) -> Path:
    target = path or preferences_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_suffix(".tmp")
    temp.write_text(prefs.model_dump_json(indent=2), encoding="utf-8")
    temp.chmod(0o600)
    temp.replace(target)
    return target
