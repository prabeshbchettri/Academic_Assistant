from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class SectionEditorWidget(QWidget):
    section_edited = Signal(str, str)  # section_heading, new_text
    regenerate_requested = Signal(str)  # section_heading
    regenerate_with_feedback_requested = Signal(str, str)  # section_heading, feedback

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter()
        layout.addWidget(splitter)

        # Section List
        self.section_list = QListWidget()
        self.section_list.currentRowChanged.connect(self._on_section_selected)
        splitter.addWidget(self.section_list)

        # Editor Area
        editor_container = QWidget()
        editor_layout = QVBoxLayout(editor_container)

        header_bar = QHBoxLayout()
        self.section_title_label = QLabel("Select a section")
        self.section_title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        header_bar.addWidget(self.section_title_label)

        self.word_count_label = QLabel("Words: 0")
        header_bar.addWidget(self.word_count_label)
        header_bar.addStretch()

        self.regen_button = QPushButton("Regenerate Section")
        self.regen_button.setObjectName("SecondaryButton")
        self.regen_button.clicked.connect(self._on_regenerate_clicked)
        header_bar.addWidget(self.regen_button)
        editor_layout.addLayout(header_bar)

        self.editor = QTextEdit()
        self.editor.textChanged.connect(self._on_text_changed)
        editor_layout.addWidget(self.editor, 1)

        feedback_label = QLabel("Feedback for this section")
        feedback_label.setObjectName("FieldLabel")
        editor_layout.addWidget(feedback_label)

        feedback_row = QHBoxLayout()
        feedback_row.setSpacing(8)

        self.feedback_input = QTextEdit()
        self.feedback_input.setObjectName("SectionFeedback")
        self.feedback_input.setPlaceholderText(
            "Tell the AI what to change in this section, e.g. "
            "shorten the procedure and add the missing trial table."
        )
        self.feedback_input.setMaximumHeight(74)
        self.feedback_input.textChanged.connect(self._update_feedback_button)
        feedback_row.addWidget(self.feedback_input, 1)

        self.feedback_regen_button = QPushButton("Regenerate with Feedback")
        self.feedback_regen_button.setObjectName("PrimaryButton")
        self.feedback_regen_button.setEnabled(False)
        self.feedback_regen_button.clicked.connect(self._on_feedback_regenerate_clicked)
        feedback_row.addWidget(
            self.feedback_regen_button, 0, Qt.AlignmentFlag.AlignBottom
        )

        editor_layout.addLayout(feedback_row)

        splitter.addWidget(editor_container)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)

        self.sections_data: dict[str, str] = {}
        self.current_section: str | None = None

    def load_report(self, report_dict: dict) -> None:
        self.section_list.clear()
        self.sections_data.clear()
        self.feedback_input.clear()

        for sec in report_dict.get("sections", []):
            heading = sec.get("heading", "")
            body = sec.get("body_markdown", "")
            self.sections_data[heading] = body
            self.section_list.addItem(heading)

        if self.section_list.count() > 0:
            self.section_list.setCurrentRow(0)

    def _on_section_selected(self, row: int) -> None:
        if row < 0 or row >= self.section_list.count():
            return
        heading = self.section_list.item(row).text()
        self.current_section = heading
        self.section_title_label.setText(heading)
        text = self.sections_data.get(heading, "")
        self.editor.blockSignals(True)
        self.editor.setPlainText(text)
        self.editor.blockSignals(False)
        self.feedback_input.clear()
        self._update_word_count()

    def _on_text_changed(self) -> None:
        if not self.current_section:
            return
        text = self.editor.toPlainText()
        self.sections_data[self.current_section] = text
        self._update_word_count()
        self.section_edited.emit(self.current_section, text)

    def _update_word_count(self) -> None:
        words = len(self.editor.toPlainText().split())
        self.word_count_label.setText(f"Words: {words}")

    def _update_feedback_button(self) -> None:
        self.feedback_regen_button.setEnabled(
            bool(self.current_section and self.feedback_input.toPlainText().strip())
        )

    def _on_regenerate_clicked(self) -> None:
        if self.current_section:
            self.regenerate_requested.emit(self.current_section)

    def _on_feedback_regenerate_clicked(self) -> None:
        feedback = self.feedback_input.toPlainText().strip()
        if not self.current_section or not feedback:
            return
        self.regenerate_with_feedback_requested.emit(self.current_section, feedback)
        self.feedback_input.clear()

    def get_edited_sections(self) -> dict[str, str]:
        return self.sections_data
