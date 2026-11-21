from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.settings import settings
from app.ui.pages.history_page import HistoryPage
from app.ui.pages.home_page import HomePage
from app.ui.pages.input_page import InputPage
from app.ui.pages.processing_page import ProcessingPage
from app.ui.pages.review_page import ReviewPage
from app.ui.pages.settings_page import SettingsPage
from app.ui.workers import WorkflowWorker
from database.db import init_db
from models.assignment import RawInput
from models.evaluation import HumanDecision

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(self, use_mock_llm: bool = False):
        super().__init__()
        self.setWindowTitle(f"{settings.app_name} — Academic Document Preparation System")
        self.resize(1100, 750)

        # Initialize local SQLite database
        init_db()

        # Load QSS styles
        qss_path = Path(__file__).resolve().parent / "styles.qss"
        if qss_path.exists():
            self.setStyleSheet(qss_path.read_text(encoding="utf-8"))

        # Setup worker thread
        self.worker = WorkflowWorker(self, use_mock_llm=use_mock_llm)
        self.worker.progress_signal.connect(self._on_worker_progress)
        self.worker.interrupt_signal.connect(self._on_worker_interrupt)
        self.worker.finished_signal.connect(self._on_worker_finished)
        self.worker.error_signal.connect(self._on_worker_error)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Left Sidebar
        self.sidebar = QFrame()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(220)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(12, 20, 12, 20)
        sidebar_layout.setSpacing(8)

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)

        self.btn_home = QPushButton("Home Dashboard")
        self.btn_home.setCheckable(True)
        self.btn_home.setChecked(True)
        self.nav_group.addButton(self.btn_home, 0)
        sidebar_layout.addWidget(self.btn_home)

        self.btn_input = QPushButton("New Assignment")
        self.btn_input.setCheckable(True)
        self.nav_group.addButton(self.btn_input, 1)
        sidebar_layout.addWidget(self.btn_input)

        self.btn_processing = QPushButton("Active Processing")
        self.btn_processing.setCheckable(True)
        self.nav_group.addButton(self.btn_processing, 2)
        sidebar_layout.addWidget(self.btn_processing)

        self.btn_review = QPushButton("Review & Approve")
        self.btn_review.setCheckable(True)
        self.nav_group.addButton(self.btn_review, 3)
        sidebar_layout.addWidget(self.btn_review)

        self.btn_history = QPushButton("Document History")
        self.btn_history.setCheckable(True)
        self.nav_group.addButton(self.btn_history, 4)
        sidebar_layout.addWidget(self.btn_history)

        sidebar_layout.addStretch()

        self.btn_settings = QPushButton("Settings")
        self.btn_settings.setCheckable(True)
        self.nav_group.addButton(self.btn_settings, 5)
        sidebar_layout.addWidget(self.btn_settings)

        main_layout.addWidget(self.sidebar)

        # Pages Stack
        self.stack = QStackedWidget()
        self.home_page = HomePage()
        self.input_page = InputPage()
        self.processing_page = ProcessingPage()
        self.review_page = ReviewPage()
        self.history_page = HistoryPage()
        self.settings_page = SettingsPage()

        self.stack.addWidget(self.home_page)
        self.stack.addWidget(self.input_page)
        self.stack.addWidget(self.processing_page)
        self.stack.addWidget(self.review_page)
        self.stack.addWidget(self.history_page)
        self.stack.addWidget(self.settings_page)

        main_layout.addWidget(self.stack)

        # Connect Navigation
        self.nav_group.idClicked.connect(self._on_nav_clicked)
        self.home_page.navigate_to_input.connect(self._on_home_navigate_input)
        self.input_page.start_generation.connect(self._on_start_generation)
        self.review_page.review_decided.connect(self._on_review_decision)

        self.home_page.refresh_recent()

    def _on_nav_clicked(self, page_id: int) -> None:
        self.stack.setCurrentIndex(page_id)
        if page_id == 0:
            self.home_page.refresh_recent()
        elif page_id == 4:
            self.history_page.refresh()

    def _on_home_navigate_input(self, source_tab: str) -> None:
        self.btn_input.setChecked(True)
        self.stack.setCurrentIndex(1)
        if source_tab == "classroom":
            self.input_page.tabs.setCurrentIndex(0)
        elif source_tab == "manual":
            self.input_page.tabs.setCurrentIndex(1)
        elif source_tab == "file":
            self.input_page.tabs.setCurrentIndex(2)

    def _on_start_generation(self, raw_input: RawInput, category: str) -> None:
        self.btn_processing.setChecked(True)
        self.stack.setCurrentIndex(2)
        self.processing_page.reset()

        self.worker.configure_new_run(raw_input, category or None)
        self.worker.start()

    def _on_worker_progress(self, node_name: str, message: str) -> None:
        self.processing_page.update_node_step(node_name, message)

    def _on_worker_interrupt(self, interrupt_type: str, data: dict) -> None:
        if interrupt_type == "missing_info":
            questions = data.get("questions", ["Additional experimental observations are needed."])
            prompt_text = "\n".join(questions)
            text, ok = QInputDialog.getMultiLineText(
                self,
                "Missing Information Required",
                f"The following details are required to complete this document:\n\n{prompt_text}",
                "",
            )
            if ok and text.strip():
                self.worker.configure_resume(self.worker.thread_id, {"provided_data": text.strip()})
                self.worker.start()
            else:
                self.worker.configure_resume(self.worker.thread_id, {"provided_data": "None provided."})
                self.worker.start()

        elif interrupt_type == "human_review":
            self.btn_review.setChecked(True)
            self.stack.setCurrentIndex(3)
            self.review_page.load_review_data(data.get("report", {}), data.get("evaluation", {}))

    def _on_review_decision(self, decision: HumanDecision) -> None:
        self.btn_processing.setChecked(True)
        self.stack.setCurrentIndex(2)
        self.processing_page.progress_log.status_label.setText("Applying decision & finalizing document...")

        self.worker.configure_resume(self.worker.thread_id, decision.model_dump())
        self.worker.start()

    def _on_worker_finished(self, final_state: dict) -> None:
        docx_path = final_state.get("docx_path", "")
        pdf_path = final_state.get("pdf_path", "")

        msg = (
            f"Document generated and exported successfully!\n\n"
            f"DOCX: {docx_path}\n"
            f"PDF: {pdf_path if pdf_path else 'LaTeX compilation pending or LibreOffice fallback'}"
        )
        QMessageBox.information(self, "Document Ready", msg)

        self.btn_history.setChecked(True)
        self.stack.setCurrentIndex(4)
        self.history_page.refresh()

    def _on_worker_error(self, error_message: str) -> None:
        QMessageBox.critical(self, "Workflow Error", f"The workflow encountered an error:\n\n{error_message}")
        self.btn_home.setChecked(True)
        self.stack.setCurrentIndex(0)
