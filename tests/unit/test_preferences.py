from __future__ import annotations

from app.preferences import (
    AppPreferences,
    DocumentDefaults,
    StudentProfile,
    category_for_document_type,
    is_profile_complete,
    load_preferences,
    save_preferences,
)


def test_preferences_round_trip(tmp_path):
    path = tmp_path / "preferences.json"
    prefs = AppPreferences(
        student=StudentProfile(
            full_name="Subesh Yadav",
            roll_number="PUL079BEI042",
            group="A",
        ),
        document=DocumentDefaults(
            document_type="Lab Sheet",
            department="Electronics and Computer Engineering",
            include_toc=False,
            logo_path="/tmp/ioe.png",
        ),
    )

    save_preferences(prefs, path)
    loaded = load_preferences(path)

    assert loaded == prefs
    assert loaded.student.full_name == "Subesh Yadav"
    assert loaded.document.include_toc is False


def test_missing_preferences_returns_defaults(tmp_path):
    loaded = load_preferences(tmp_path / "missing.json")

    assert loaded.student.full_name == ""
    assert loaded.document.institution == "Institute of Engineering, Pulchowk Campus"
    assert loaded.document.include_front_page is True


def test_invalid_preferences_file_falls_back_to_defaults(tmp_path):
    path = tmp_path / "preferences.json"
    path.write_text("{not valid json", encoding="utf-8")

    loaded = load_preferences(path)

    assert loaded.student.full_name == ""


def test_document_type_mapping_and_profile_completion():
    assert category_for_document_type("Lab Sheet") == "initial_lab"
    assert category_for_document_type("Final Lab Report") == "final_lab"
    assert category_for_document_type("Unknown") == "assignment"

    assert is_profile_complete(StudentProfile(full_name="A", roll_number="1")) is True
    assert is_profile_complete(StudentProfile(full_name="A", roll_number="")) is False
