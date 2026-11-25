from __future__ import annotations

import logging

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ai.llm.factory import build_provider
from ai.retriever import RagRetriever
from app.preferences import (
    DOCUMENT_TYPES,
    AppPreferences,
    DocumentDefaults,
    StudentProfile,
    category_for_document_type,
    load_preferences,
    save_preferences,
)
from database.db import get_session
from database.models import ReferenceDocumentTable
from integrations.file_parser import parse_file
from models.assignment import RawInput

logger = logging.getLogger(__name__)


class PreparationForm(QWidget):
    def __init__(
        self,
        parent: QWidget | None = None,
        preferences: AppPreferences | None = None,
    ):
        super().__init__(parent)
        self.preferences = preferences or load_preferences()
        self._build()
        self.load_preferences(self.preferences)

    def _build(self) -> None:
        grid = QGridLayout(self)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(14)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        grid.addWidget(self._build_student_card(), 0, 0)
        grid.addWidget(self._build_document_card(), 0, 1)
        grid.addWidget(self._build_notes_card(), 1, 0, 1, 2)

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

    def _build_student_card(self) -> QFrame:
        card, layout = self._card("Student & submission")
        form = QFormLayout()
        form.setSpacing(8)

        self.title_input = QLineEdit()
        self.course_input = QLineEdit()
        self.name_input = QLineEdit()
        self.roll_input = QLineEdit()
        self.group_input = QLineEdit()
        # Kept as attributes for preferences round-trip compatibility, excluded from IOE front page
        self.program_input = QLineEdit()
        self.semester_input = QLineEdit()
        self.section_input = QLineEdit()
        self.submitted_to_input = QLineEdit()
        self.submitted_to_input.setPlaceholderText("Defaults to full department name")
        self.date_input = QDateEdit(QDate.currentDate())
        self.date_input.setCalendarPopup(True)
        self.date_input.setDisplayFormat("MMMM d, yyyy")

        self.assignment_file_input = QLineEdit()
        self.assignment_file_input.setPlaceholderText("Optional local PDF / DOCX / TXT sheet")
        file_row = QHBoxLayout()
        file_row.setSpacing(6)
        file_row.addWidget(self.assignment_file_input, 1)
        browse_file = QPushButton("Browse")
        browse_file.setObjectName("SecondaryButton")
        browse_file.clicked.connect(self._browse_assignment_file)
        file_row.addWidget(browse_file)

        self.rag_file_input = QLineEdit()
        self.rag_file_input.setPlaceholderText("Optional lab manual / lecture PDF for RAG")
        rag_row = QHBoxLayout()
        rag_row.setSpacing(6)
        rag_row.addWidget(self.rag_file_input, 1)
        index_rag_btn = QPushButton("Index RAG")
        index_rag_btn.setObjectName("SecondaryButton")
        index_rag_btn.clicked.connect(self._browse_and_index_rag)
        rag_row.addWidget(index_rag_btn)

        form.addRow("Document title", self.title_input)
        form.addRow("Course / subject", self.course_input)
        form.addRow("Full name", self.name_input)
        form.addRow("Roll number", self.roll_input)
        form.addRow("Group", self.group_input)
        form.addRow("Submitted to", self.submitted_to_input)
        form.addRow("Submission date", self.date_input)
        form.addRow("Attachment", file_row)
        form.addRow("Reference RAG", rag_row)
        layout.addLayout(form)
        return card

    def _build_document_card(self) -> QFrame:
        card, layout = self._card("Document & front page")
        form = QFormLayout()
        form.setSpacing(8)

        self.type_combo = QComboBox()
        self.type_combo.addItem("Auto-detect from assignment", "")
        for document_type in DOCUMENT_TYPES:
            self.type_combo.addItem(document_type, document_type)
        form.addRow("Document type", self.type_combo)

        self.include_front_page = QCheckBox("Generate IOE Pulchowk front page")
        form.addRow("", self.include_front_page)

        self.institution_input = QLineEdit()
        self.university_input = QLineEdit()
        self.campus_input = QLineEdit()
        self.department_input = QLineEdit()
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
        form.addRow("Department", self.department_input)
        form.addRow("Logo", logo_row)

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

        layout.addLayout(form)
        return card

    def _build_notes_card(self) -> QFrame:
        card, layout = self._card("Instructions & considerations")
        self.use_assignment_instructions = QCheckBox(
            "Use formatting and instructions already present in the assignment"
        )
        layout.addWidget(self.use_assignment_instructions)

        layout.addWidget(QLabel("Extra formatting notes"))
        self.format_notes = QTextEdit()
        self.format_notes.setMaximumHeight(80)
        self.format_notes.setPlaceholderText(
            "Example: 12 pt Times New Roman, 1.25 spacing, "
            "or follow a specific lab-sheet layout."
        )
        layout.addWidget(self.format_notes)

        layout.addWidget(QLabel("Additional information / measurements for the AI"))
        self.extra_notes = QTextEdit()
        self.extra_notes.setMaximumHeight(80)
        self.extra_notes.setPlaceholderText(
            "Add prompt details, experimental measurements (e.g. V = 12V, R = 4 ohms), "
            "assumptions, or teacher instructions."
        )
        layout.addWidget(self.extra_notes)

        self.save_defaults = QCheckBox("Save these details as my defaults")
        self.save_defaults.setChecked(True)
        layout.addWidget(self.save_defaults)
        return card

    def _browse_logo(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select institution logo",
            "",
            "Images (*.png *.jpg *.jpeg *.webp)",
        )
        if path:
            self.logo_input.setText(path)

    def _browse_assignment_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select local assignment file",
            "",
            "Documents (*.pdf *.docx *.doc *.txt *.md);;All Files (*)",
        )
        if path:
            self.assignment_file_input.setText(path)

    def _browse_and_index_rag(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select course reference material for RAG",
            "",
            "Documents (*.pdf *.docx *.doc *.txt *.md);;All Files (*)",
        )
        if not path:
            return
        course_name = self.course_input.text().strip() or "general"
        try:
            parsed = parse_file(path)
            provider = build_provider()
            retriever = RagRetriever(llm=provider)
            chunks = retriever.index_document(course_name, path.split("/")[-1], parsed.text)
            with get_session() as session:
                session.add(
                    ReferenceDocumentTable(
                        course_id=course_name,
                        filename=path.split("/")[-1],
                        path=path,
                        chunk_count=chunks,
                    )
                )
                session.commit()
            self.rag_file_input.setText(f"{path} ({chunks} chunks)")
            QMessageBox.information(
                self,
                "RAG Reference Indexed",
                f"Indexed {chunks} chunk(s) into course collection '{course_name}'.",
            )
        except Exception as exc:
            logger.warning("RAG indexing failed: %s", exc)
            QMessageBox.warning(self, "RAG Indexing Failed", str(exc))

    def load_preferences(self, prefs: AppPreferences) -> None:
        self.preferences = prefs
        student = prefs.student
        document = prefs.document

        self.name_input.setText(student.full_name)
        self.roll_input.setText(student.roll_number)
        self.group_input.setText(student.group)
        self.program_input.setText(student.program)
        self.semester_input.setText(student.semester)
        self.section_input.setText(student.section)

        index = self.type_combo.findData(document.document_type)
        if index >= 0:
            self.type_combo.setCurrentIndex(index)
        self.include_front_page.setChecked(document.include_front_page)
        self.institution_input.setText(document.institution)
        self.university_input.setText(document.university)
        self.campus_input.setText(document.campus)
        self.department_input.setText(
            document.department or "Department of Electronics & Computer Engineering"
        )
        self.submitted_to_input.setText(
            document.department or "Department of Electronics & Computer Engineering"
        )
        self.logo_input.setText(document.logo_path)
        self.include_toc.setChecked(document.include_toc)
        self.citation_combo.setCurrentText(document.citation_style)
        self.font_combo.setCurrentText(document.font_family)
        self.font_size.setValue(document.font_size)
        self.line_spacing.setValue(document.line_spacing)
        self.margin_input.setValue(document.margin_inches)
        self.format_notes.setPlainText(document.format_notes)

    def set_assignment(self, title: str, course: str | None = None) -> None:
        self.title_input.setText(title)
        self.course_input.setText(course or "")

    def validate(self) -> str | None:
        if not self.title_input.text().strip():
            return "Enter a document title."
        if self.include_front_page.isChecked():
            if not self.name_input.text().strip():
                return "Enter your full name."
            if not self.roll_input.text().strip():
                return "Enter your roll number."
        return None

    def _selected_document_type(self) -> str:
        data = self.type_combo.currentData()
        if data:
            return str(data)
        return "Academic Assignment"

    def _collect(self) -> tuple[StudentProfile, DocumentDefaults]:
        dept = (
            self.department_input.text().strip()
            or "Department of Electronics & Computer Engineering"
        )
        student = StudentProfile(
            full_name=self.name_input.text().strip(),
            roll_number=self.roll_input.text().strip(),
            group=self.group_input.text().strip(),
            program=self.program_input.text().strip(),
            department=dept,
            semester=self.semester_input.text().strip(),
            section=self.section_input.text().strip(),
            email=self.preferences.student.email,
        )
        document = DocumentDefaults(
            document_type=self._selected_document_type(),
            institution=self.institution_input.text().strip(),
            university=self.university_input.text().strip(),
            campus=self.campus_input.text().strip(),
            department=dept,
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
        return student, document

    def apply_to_raw(self, raw: RawInput) -> tuple[RawInput, str]:
        student, document = self._collect()
        metadata = dict(raw.metadata)
        metadata.update(
            {
                "student_profile": student.model_dump(mode="json"),
                "document_preferences": document.model_dump(mode="json"),
                "document_type": document.document_type,
                "assignment_notes": self.extra_notes.toPlainText().strip(),
                "use_assignment_instructions": self.use_assignment_instructions.isChecked(),
                "submitted_to": (
                    self.submitted_to_input.text().strip() or document.department
                ),
                "submission_date": self.date_input.date().toString("MMMM d, yyyy"),
            }
        )

        attached_file = self.assignment_file_input.text().strip() or raw.file_path
        updated = raw.model_copy(
            update={
                "title": self.title_input.text().strip(),
                "course_name": self.course_input.text().strip() or None,
                "file_path": attached_file,
                "metadata": metadata,
            }
        )

        if self.type_combo.currentData():
            category = category_for_document_type(document.document_type)
        else:
            category = ""

        if self.save_defaults.isChecked():
            save_preferences(AppPreferences(student=student, document=document))

        return updated, category
