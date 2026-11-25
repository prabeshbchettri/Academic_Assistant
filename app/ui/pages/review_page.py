from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTabWidget,
    QTextEdit,
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
        layout.setSpacing(14)

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
        self.editor_widget.regenerate_with_feedback_requested.connect(
            self._on_section_feedback_regenerate
        )

        self.tabs.addTab(self.preview_widget, "Document Preview")
        self.tabs.addTab(self.editor_widget, "Section Editor & Revisions")
        layout.addWidget(self.tabs)

        # Overall document feedback
        overall_card = QFrame()
        overall_card.setProperty("class", "Card")
        overall_layout = QHBoxLayout(overall_card)
        overall_layout.setContentsMargins(16, 12, 16, 12)
        overall_layout.setSpacing(12)

        overall_copy = QVBoxLayout()
        overall_copy.setSpacing(2)
        overall_title = QLabel("Overall improvement")
        overall_title.setObjectName("CardTitle")
        overall_copy.addWidget(overall_title)
        overall_hint = QLabel(
            "Feedback here is applied to every section of the document."
        )
        overall_hint.setObjectName("Muted")
        overall_hint.setWordWrap(True)
        overall_copy.addWidget(overall_hint)
        overall_layout.addLayout(overall_copy, 1)

        self.overall_feedback = QTextEdit()
        self.overall_feedback.setObjectName("OverallFeedback")
        self.overall_feedback.setPlaceholderText(
            "Describe whole-document improvements, e.g. tighten every section to "
            "the word limits and add a proper discussion."
        )
        self.overall_feedback.setMaximumHeight(68)
        self.overall_feedback.textChanged.connect(self._update_overall_button)
        overall_layout.addWidget(self.overall_feedback, 2)

        self.overall_regen_btn = QPushButton("Regenerate All with Feedback")
        self.overall_regen_btn.setObjectName("PrimaryButton")
        self.overall_regen_btn.setEnabled(False)
        self.overall_regen_btn.clicked.connect(self._on_overall_feedback_clicked)
        overall_layout.addWidget(self.overall_regen_btn)

        layout.addWidget(overall_card)

        # Actions Bar
        actions_card = QFrame()
        actions_card.setProperty("class", "Card")
        a_layout = QHBoxLayout(actions_card)

        self.regenerate_all_btn = QPushButton("Regenerate Failed Sections")
        self.regenerate_all_btn.setObjectName("SecondaryButton")
        self.regenerate_all_btn.clicked.connect(self._on_regenerate_all_clicked)
        a_layout.addWidget(self.regenerate_all_btn)

        self.apply_edits_btn = QPushButton("Save Edits & Refresh")
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

    def load_review_data(
        self,
        report_dict: dict,
        eval_dict: dict,
        telemetry_dict: dict | None = None,
    ) -> None:
        self.current_report_dict = report_dict
        self.current_eval_dict = eval_dict

        self.preview_widget.display_report(report_dict)
        self.editor_widget.load_report(report_dict)
        self.overall_feedback.clear()
        self._update_overall_button()

        overall_passed = eval_dict.get("overall_passed", False)
        failed_secs = eval_dict.get("failed_sections", [])
        score = float(eval_dict.get("overall_score", 0.0) or 0.0)
        telemetry = telemetry_dict or {}
        telemetry_suffix = ""
        if telemetry.get("total_calls"):
            providers = "/".join(telemetry.get("providers_used", [])) or "llm"
            latency_s = float(telemetry.get("total_latency_ms", 0.0)) / 1000.0
            tokens = int(telemetry.get("total_tokens", 0) or 0)
            telemetry_suffix = (
                f" | Provider: {providers} | Calls: {telemetry['total_calls']}"
                f" | Tokens: {tokens} | Time: {latency_s:.1f}s"
            )

        if overall_passed:
            self._set_badge(f"Status: PASSED ({score:.2f})", "BadgePass")
            self.eval_details_label.setText(
                f"Weighted rubric score {score:.2f} — word counts, structure, and "
                f"citations verified.{telemetry_suffix}"
            )
            self.regenerate_all_btn.setEnabled(False)
        else:
            self._set_badge(
                f"Status: {len(failed_secs)} SECTION(S) NEED ATTENTION ({score:.2f})",
                "BadgeWarning",
            )
            self.eval_details_label.setText(
                f"Issues detected in: {', '.join(failed_secs)}. "
                f"You can edit, regenerate, or leave feedback.{telemetry_suffix}"
            )
            self.regenerate_all_btn.setEnabled(True)

    def _set_badge(self, text: str, object_name: str) -> None:
        self.status_badge.setText(text)
        self.status_badge.setObjectName(object_name)
        style = self.status_badge.style()
        style.unpolish(self.status_badge)
        style.polish(self.status_badge)
        self.status_badge.update()

    def _update_overall_button(self) -> None:
        self.overall_regen_btn.setEnabled(
            bool(self.overall_feedback.toPlainText().strip())
        )

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
        decision = HumanDecision(
            decision=DecisionType.REGENERATE,
            regenerate_sections=[section_name],
        )
        self.review_decided.emit(decision)

    def _on_section_feedback_regenerate(self, section_name: str, feedback: str) -> None:
        decision = HumanDecision(
            decision=DecisionType.REGENERATE,
            feedback=feedback,
            regenerate_sections=[section_name],
        )
        self.review_decided.emit(decision)

    def _on_overall_feedback_clicked(self) -> None:
        feedback = self.overall_feedback.toPlainText().strip()
        if not feedback:
            return
        decision = HumanDecision(
            decision=DecisionType.REGENERATE,
            feedback=feedback,
            regenerate_sections=[],
        )
        self.review_decided.emit(decision)
