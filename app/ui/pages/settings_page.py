from __future__ import annotations

from pathlib import Path

from pydantic import SecretStr
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.preferences import (
    DOCUMENT_TYPES,
    AppPreferences,
    DocumentDefaults,
    StudentProfile,
    load_preferences,
    save_preferences,
)
from app.settings import settings
from integrations.google_auth import is_authenticated


class SettingsPage(QWidget):
    settings_saved = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll)

        content = QWidget()
        scroll.setWidget(content)

        layout = QVBoxLayout(content)
        layout.setContentsMargins(30, 28, 30, 32)
        layout.setSpacing(16)

        title = QLabel("Settings")
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        subtitle = QLabel(
            "Your profile is reused for every document. Formatting defaults can still "
            "be changed for each assignment."
        )
        subtitle.setObjectName("PageSubtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        layout.addWidget(self._build_profile_card())
        layout.addWidget(self._build_document_card())
        layout.addWidget(self._build_ai_card())
        layout.addWidget(self._build_google_card())

        save_btn = QPushButton("Save Settings")
        save_btn.setObjectName("PrimaryButton")
        save_btn.clicked.connect(self._save_settings)
        layout.addWidget(save_btn, 0)
        layout.addStretch()

        self.reload_preferences()

    def _card(self, title: str) -> tuple[QFrame, QVBoxLayout]:
        card = QFrame()
        card.setProperty("class", "Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        heading = QLabel(title)
        heading.setObjectName("CardTitle")
        layout.addWidget(heading)
        return card, layout

    def _build_profile_card(self) -> QFrame:
        card, layout = self._card("Student profile")
        form = QFormLayout()
        form.setSpacing(8)

        self.full_name_input = QLineEdit()
        self.roll_input = QLineEdit()
        self.group_input = QLineEdit()
        self.program_input = QLineEdit()
        self.department_input = QLineEdit()
        self.semester_input = QLineEdit()
        self.section_input = QLineEdit()
        self.email_input = QLineEdit()

        form.addRow("Full name", self.full_name_input)
        form.addRow("Roll number", self.roll_input)
        form.addRow("Group", self.group_input)
        form.addRow("Program", self.program_input)
        form.addRow("Department", self.department_input)
        form.addRow("Semester", self.semester_input)
        form.addRow("Section", self.section_input)
        form.addRow("Email", self.email_input)
        layout.addLayout(form)
        return card

    def _build_document_card(self) -> QFrame:
        card, layout = self._card("Document defaults")
        form = QFormLayout()
        form.setSpacing(8)

        self.document_type_combo = QComboBox()
        for document_type in DOCUMENT_TYPES:
            self.document_type_combo.addItem(document_type, document_type)
        form.addRow("Default document type", self.document_type_combo)

        self.institution_input = QLineEdit()
        self.university_input = QLineEdit()
        self.campus_input = QLineEdit()
        self.document_department_input = QLineEdit()
        self.logo_input = QLineEdit()
        self.logo_input.setPlaceholderText("Optional PNG/JPG logo")

        logo_row = QHBoxLayout()
        logo_row.setSpacing(6)
        logo_row.addWidget(self.logo_input, 1)
        browse = QPushButton("Browse")
        browse.setObjectName("SecondaryButton")
        browse.clicked.connect(self._browse_logo)
        logo_row.addWidget(browse)

        form.addRow("Institution", self.institution_input)
        form.addRow("University", self.university_input)
        form.addRow("Campus", self.campus_input)
        form.addRow("Department", self.document_department_input)
        form.addRow("Logo", logo_row)

        self.include_front_page = QCheckBox("Generate front page by default")
        form.addRow("", self.include_front_page)
        self.include_toc = QCheckBox("Include table of contents")
        form.addRow("", self.include_toc)

        self.citation_combo = QComboBox()
        self.citation_combo.addItems(["IEEE", "APA", "MLA", "Chicago"])
        form.addRow("Citation style", self.citation_combo)

        self.font_combo = QComboBox()
        self.font_combo.addItems(
            ["Times New Roman", "Liberation Serif", "Calibri", "Arial"]
        )
        form.addRow("Font", self.font_combo)

        self.font_size = QSpinBox()
        self.font_size.setRange(9, 14)
        form.addRow("Font size", self.font_size)

        self.line_spacing = QDoubleSpinBox()
        self.line_spacing.setRange(1.0, 2.0)
        self.line_spacing.setSingleStep(0.05)
        form.addRow("Line spacing", self.line_spacing)

        self.margin_input = QDoubleSpinBox()
        self.margin_input.setRange(0.5, 1.5)
        self.margin_input.setSingleStep(0.25)
        self.margin_input.setSuffix(" in")
        form.addRow("Page margin", self.margin_input)

        self.format_notes = QTextEdit()
        self.format_notes.setMaximumHeight(80)
        self.format_notes.setPlaceholderText(
            "Default formatting instructions to reuse, e.g. lab-sheet layout, "
            "two-column format, or specific heading rules."
        )
        form.addRow("Formatting notes", self.format_notes)
        layout.addLayout(form)
        return card

    def _build_ai_card(self) -> QFrame:
        card, layout = self._card("AI & export")
        form = QFormLayout()
        form.setSpacing(8)

        self.provider_combo = QComboBox()
        self.provider_combo.addItem("NVIDIA NIM", "nvidia")
        self.provider_combo.addItem("Google Gemini", "gemini")
        form.addRow("AI provider", self.provider_combo)

        self.nvidia_key_input = QLineEdit()
        self.nvidia_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.nvidia_key_input.setPlaceholderText("Leave blank to keep the saved key")
        form.addRow("NVIDIA API key", self.nvidia_key_input)

        self.nvidia_model_combo = QComboBox()
        self.nvidia_model_combo.setEditable(True)
        self.nvidia_model_combo.addItems(
            [
                "nvidia/nemotron-3-ultra-550b-a55b",
                "nvidia/llama-3.3-nemotron-super-49b-v1.5",
                "nvidia/nemotron-4-340b-instruct",
            ]
        )
        form.addRow("NVIDIA model", self.nvidia_model_combo)

        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setPlaceholderText("Optional Gemini fallback key")
        form.addRow("Gemini API key (fallback)", self.api_key_input)

        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        self.model_combo.addItems(
            [
                "gemini-2.5-flash-lite",
                "gemini-2.5-flash",
                "gemini-2.5-pro",
            ]
        )
        form.addRow("Gemini model (fallback)", self.model_combo)

        self.pdf_engine_combo = QComboBox()
        self.pdf_engine_combo.addItems(["tectonic", "xelatex", "libreoffice"])
        form.addRow("PDF engine", self.pdf_engine_combo)
        layout.addLayout(form)
        return card

    def _build_google_card(self) -> QFrame:
        card, layout = self._card("Google Classroom")
        row = QHBoxLayout()
        self.google_status_label = QLabel("Status: Not Connected")
        self.google_status_label.setObjectName("Muted")
        row.addWidget(self.google_status_label)
        row.addStretch()

        self.connect_google_btn = QPushButton("Connect / Re-authorize")
        self.connect_google_btn.setObjectName("SecondaryButton")
        self.connect_google_btn.clicked.connect(self._test_google_oauth)
        row.addWidget(self.connect_google_btn)
        layout.addLayout(row)
        return card

    def reload_preferences(self) -> None:
        prefs = load_preferences()
        student = prefs.student
        document = prefs.document

        self.full_name_input.setText(student.full_name)
        self.roll_input.setText(student.roll_number)
        self.group_input.setText(student.group)
        self.program_input.setText(student.program)
        self.department_input.setText(student.department)
        self.semester_input.setText(student.semester)
        self.section_input.setText(student.section)
        self.email_input.setText(student.email)

        index = self.document_type_combo.findData(document.document_type)
        if index >= 0:
            self.document_type_combo.setCurrentIndex(index)
        self.institution_input.setText(document.institution)
        self.university_input.setText(document.university)
        self.campus_input.setText(document.campus)
        self.document_department_input.setText(document.department)
        self.logo_input.setText(document.logo_path)
        self.include_front_page.setChecked(document.include_front_page)
        self.include_toc.setChecked(document.include_toc)
        self.citation_combo.setCurrentText(document.citation_style)
        self.font_combo.setCurrentText(document.font_family)
        self.font_size.setValue(document.font_size)
        self.line_spacing.setValue(document.line_spacing)
        self.margin_input.setValue(document.margin_inches)
        self.format_notes.setPlainText(document.format_notes)

        provider_index = self.provider_combo.findData(settings.llm_provider.lower())
        if provider_index >= 0:
            self.provider_combo.setCurrentIndex(provider_index)
        self.nvidia_key_input.setText(settings.nvidia_api_key_str)
        self.nvidia_model_combo.setCurrentText(settings.nvidia_model)
        self.api_key_input.setText(settings.gemini_api_key_str)
        self.model_combo.setCurrentText(settings.gemini_model)
        self.pdf_engine_combo.setCurrentText(settings.pdf_engine)
        self._refresh_google_status()

    def _refresh_google_status(self) -> None:
        connected = is_authenticated()
        self.google_status_label.setText(
            "Status: Connected" if connected else "Status: Not Connected"
        )

    def _browse_logo(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select institution logo",
            "",
            "Images (*.png *.jpg *.jpeg *.webp)",
        )
        if path:
            self.logo_input.setText(path)

    def _test_google_oauth(self) -> None:
        try:
            from integrations.google_auth import get_credentials

            creds = get_credentials()
            if creds and creds.valid:
                self._refresh_google_status()
                QMessageBox.information(
                    self,
                    "Google OAuth",
                    "Google account authorized successfully.",
                )
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Google OAuth Error",
                f"OAuth flow could not complete: {exc}",
            )

    def _save_settings(self) -> None:
        student = StudentProfile(
            full_name=self.full_name_input.text().strip(),
            roll_number=self.roll_input.text().strip(),
            group=self.group_input.text().strip(),
            program=self.program_input.text().strip(),
            department=self.department_input.text().strip(),
            semester=self.semester_input.text().strip(),
            section=self.section_input.text().strip(),
            email=self.email_input.text().strip(),
        )
        document = DocumentDefaults(
            document_type=str(self.document_type_combo.currentData()),
            institution=self.institution_input.text().strip(),
            university=self.university_input.text().strip(),
            campus=self.campus_input.text().strip(),
            department=self.document_department_input.text().strip(),
            include_front_page=self.include_front_page.isChecked(),
            include_toc=self.include_toc.isChecked(),
            citation_style=self.citation_combo.currentText(),
            font_family=self.font_combo.currentText(),
            font_size=self.font_size.value(),
            line_spacing=self.line_spacing.value(),
            margin_inches=self.margin_input.value(),
            logo_path=self.logo_input.text().strip(),
            format_notes=self.format_notes.toPlainText().strip(),
        )
        save_preferences(AppPreferences(student=student, document=document))

        new_provider = str(self.provider_combo.currentData())
        new_nvidia_key = self.nvidia_key_input.text().strip()
        new_nvidia_model = self.nvidia_model_combo.currentText().strip()
        new_gemini_key = self.api_key_input.text().strip()
        new_gemini_model = self.model_combo.currentText().strip()
        new_pdf = self.pdf_engine_combo.currentText()

        settings.llm_provider = new_provider
        if new_nvidia_key:
            settings.nvidia_api_key = SecretStr(new_nvidia_key)
        if new_nvidia_model:
            settings.nvidia_model = new_nvidia_model
        if new_gemini_key:
            settings.gemini_api_key = SecretStr(new_gemini_key)
        if new_gemini_model:
            settings.gemini_model = new_gemini_model
        settings.pdf_engine = new_pdf

        updates = {
            "LLM_PROVIDER": new_provider,
            "NVIDIA_MODEL": settings.nvidia_model,
            "NVIDIA_BASE_URL": settings.nvidia_base_url,
            "NVIDIA_MAX_OUTPUT_TOKENS": str(settings.nvidia_max_output_tokens),
            "GEMINI_MODEL": settings.gemini_model,
            "PDF_ENGINE": new_pdf,
        }
        if new_nvidia_key:
            updates["NVIDIA_API_KEY"] = new_nvidia_key
        if new_gemini_key:
            updates["GEMINI_API_KEY"] = new_gemini_key
        self._write_env(updates)
        self.settings_saved.emit()
        QMessageBox.information(self, "Settings", "Settings saved successfully.")

    @staticmethod
    def _write_env(updates: dict[str, str]) -> None:
        env_file = Path(__file__).resolve().parent.parent.parent / ".env"
        lines = env_file.read_text(encoding="utf-8").splitlines() if env_file.exists() else []
        seen: set[str] = set()
        for index, line in enumerate(lines):
            key = line.split("=", 1)[0].strip()
            if key in updates:
                lines[index] = f"{key}={updates[key]}"
                seen.add(key)
        for key, value in updates.items():
            if key not in seen:
                lines.append(f"{key}={value}")
        env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
