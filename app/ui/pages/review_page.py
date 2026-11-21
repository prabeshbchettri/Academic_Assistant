from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.ui.widgets.preview import DocumentPreviewWidget
from app.ui.widgets.section_editor import SectionEditorWidget
from models.evaluation import DecisionType, HumanDecision


class ReviewPage(QWidget):
    review_decided = Signal(HumanDecision)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header bar with evaluation status badge
        header_bar = QHBoxLayout()
        title = QLabel("Human-in-the-Loop Review & Approval")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #1B365D;")
        header_bar.addWidget(title)
        header_bar.addStretch()

        self.status_badge = QLabel("Verification: Pending")
        self.status_badge.setObjectName("BadgePass")
        header_bar.addWidget(self.status_badge)
        layout.addLayout(header_bar)

        self.eval_details_label = QLabel("")
        self.eval_details_label.setStyleSheet("color: #475569; font-size: 13px;")
        layout.addWidget(self.eval_details_label)

        # Tabs: Formatted Preview vs Section-by-Section Editor
        self.tabs = QTabWidget()
        self.preview_widget = DocumentPreviewWidget()
        self.editor_widget = SectionEditorWidget()
        self.editor_widget.regenerate_requested.connect(self._on_single_section_regenerate)

        self.tabs.addTab(self.preview_widget, "Document Preview")
        self.tabs.addTab(self.editor_widget, "Section Editor & Revisions")
        layout.addWidget(self.tabs)

        # Actions Bar
        actions_card = QFrame()
        actions_card.setProperty("class", "Card")
        a_layout = QHBoxLayout(actions_card)

        self.regenerate_all_btn = QPushButton("Regenerate Failed Sections")
        self.regenerate_all_btn.setObjectName("SecondaryButton")
        self.regenerate_all_btn.clicked.connect(self._on_regenerate_all_clicked)
        a_layout.addWidget(self.regenerate_all_btn)

        self.apply_edits_btn = QPushButton("Apply My Edits")
        self.apply_edits_btn.setObjectName("SecondaryButton")
        self.apply_edits_btn.clicked.connect(self._on_apply_edits_clicked)
        a_layout.addWidget(self.apply_edits_btn)

        a_layout.addStretch()

        self.approve_btn = QPushButton("Approve & Export (DOCX + PDF)")
        self.approve_btn.setObjectName("PrimaryButton")
        self.approve_btn.clicked.connect(self._on_approve_clicked)
        a_layout.addWidget(self.approve_btn)

        layout.addWidget(actions_card)

        self.current_report_dict: dict = {}
        self.current_eval_dict: dict = {}

    def load_review_data(self, report_dict: dict, eval_dict: dict) -> None:
        self.current_report_dict = report_dict
        self.current_eval_dict = eval_dict

        self.preview_widget.display_report(report_dict)
        self.editor_widget.load_report(report_dict)

        overall_passed = eval_dict.get("overall_passed", False)
        failed_secs = eval_dict.get("failed_sections", [])

        if overall_passed:
            self.status_badge.setText("Status: ALL VERIFICATION CHECKS PASSED")
            self.status_badge.setObjectName("BadgePass")
            self.eval_details_label.setText("Deterministic word counts, structure, formulas, and rubric scores are verified.")
            self.regenerate_all_btn.setEnabled(False)
        else:
            self.status_badge.setText(f"Status: {len(failed_secs)} SECTION(S) NEED ATTENTION")
            self.status_badge.setObjectName("BadgeWarning")
            self.eval_details_label.setText(f"Issues detected in: {', '.join(failed_secs)}. You can edit or regenerate.")
            self.regenerate_all_btn.setEnabled(True)

    def _on_approve_clicked(self) -> None:
        edited = self.editor_widget.get_edited_sections()
        decision = HumanDecision(decision=DecisionType.APPROVE, edited_sections=edited)
        self.review_decided.emit(decision)

    def _on_apply_edits_clicked(self) -> None:
        edited = self.editor_widget.get_edited_sections()
        decision = HumanDecision(decision=DecisionType.EDIT, edited_sections=edited)
        self.review_decided.emit(decision)

    def _on_regenerate_all_clicked(self) -> None:
        failed = self.current_eval_dict.get("failed_sections", [])
        decision = HumanDecision(decision=DecisionType.REGENERATE, regenerate_sections=failed)
        self.review_decided.emit(decision)

    def _on_single_section_regenerate(self, section_name: str) -> None:
        decision = HumanDecision(decision=DecisionType.REGENERATE, regenerate_sections=[section_name])
        self.review_decided.emit(decision)
