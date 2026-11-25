from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.preferences import load_preferences
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
        self.setWindowTitle(f"{settings.app_name} — Student Workspace")
        self.resize(1180, 800)
        self.setMinimumSize(980, 680)

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
        self.sidebar.setFixedWidth(250)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(16, 22, 16, 18)
        sidebar_layout.setSpacing(8)

        brand = QFrame()
        brand.setObjectName("Brand")
        brand_layout = QVBoxLayout(brand)
        brand_layout.setContentsMargins(8, 0, 8, 16)
        brand_layout.setSpacing(2)
        brand_title = QLabel("Academic AI")
        brand_title.setObjectName("BrandTitle")
        brand_layout.addWidget(brand_title)
        brand_subtitle = QLabel("Student Workspace")
        brand_subtitle.setObjectName("BrandSubtitle")
        brand_layout.addWidget(brand_subtitle)
        sidebar_layout.addWidget(brand)

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)

        self.btn_home = QPushButton("Dashboard")
        self.btn_home.setObjectName("NavButton")
        self.btn_home.setCheckable(True)
        self.btn_home.setChecked(True)
        self.nav_group.addButton(self.btn_home, 0)
        sidebar_layout.addWidget(self.btn_home)

        self.btn_input = QPushButton("Classroom & Input")
        self.btn_input.setObjectName("NavButton")
        self.btn_input.setCheckable(True)
        self.nav_group.addButton(self.btn_input, 1)
        sidebar_layout.addWidget(self.btn_input)

        self.btn_processing = QPushButton("Active Processing")
        self.btn_processing.setObjectName("NavButton")
        self.btn_processing.setCheckable(True)
        self.nav_group.addButton(self.btn_processing, 2)
        sidebar_layout.addWidget(self.btn_processing)

        self.btn_review = QPushButton("Review & Approve")
        self.btn_review.setObjectName("NavButton")
        self.btn_review.setCheckable(True)
        self.nav_group.addButton(self.btn_review, 3)
        sidebar_layout.addWidget(self.btn_review)

        self.btn_history = QPushButton("Document History")
        self.btn_history.setObjectName("NavButton")
        self.btn_history.setCheckable(True)
        self.nav_group.addButton(self.btn_history, 4)
        sidebar_layout.addWidget(self.btn_history)

        sidebar_layout.addStretch()

        self.sidebar_user = QFrame()
        self.sidebar_user.setObjectName("SidebarUser")
        user_layout = QVBoxLayout(self.sidebar_user)
        user_layout.setContentsMargins(12, 10, 12, 10)
        user_layout.setSpacing(2)
        self.sidebar_user_name = QLabel("Student")
        self.sidebar_user_name.setObjectName("SidebarUserName")
        user_layout.addWidget(self.sidebar_user_name)
        self.sidebar_user_meta = QLabel("Complete your profile")
        self.sidebar_user_meta.setObjectName("SidebarUserMeta")
        user_layout.addWidget(self.sidebar_user_meta)
        sidebar_layout.addWidget(self.sidebar_user)

        self.btn_settings = QPushButton("Settings")
        self.btn_settings.setObjectName("NavButton")
        self.btn_settings.setCheckable(True)
        self.nav_group.addButton(self.btn_settings, 5)
        sidebar_layout.addWidget(self.btn_settings)

        main_layout.addWidget(self.sidebar)

        # Pages Stack
        self.stack = QStackedWidget()
        self.home_page = HomePage(auto_sync=not use_mock_llm)
        self.input_page = InputPage(auto_load=not use_mock_llm)
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
        self.home_page.open_input.connect(self._on_home_navigate_input)
        self.home_page.open_course.connect(self._on_open_course)
        self.home_page.open_settings.connect(self._on_open_settings)
        self.home_page.open_history.connect(self._on_open_history)
        self.input_page.start_generation.connect(self._on_start_generation)
        self.review_page.review_decided.connect(self._on_review_decision)
        self.history_page.edit_requested.connect(self._on_edit_requested)
        self.settings_page.settings_saved.connect(self._on_settings_saved)

        self.refresh_sidebar_profile()
        self.home_page.refresh_recent()

    def _on_nav_clicked(self, page_id: int) -> None:
        self.stack.setCurrentIndex(page_id)
        if page_id == 0:
            self.home_page.refresh_profile()
            self.home_page.refresh_recent()
        elif page_id == 1:
            self.input_page.refresh_preferences()
        elif page_id == 4:
            self.history_page.refresh()
        elif page_id == 5:
            self.settings_page.reload_preferences()

    def _on_home_navigate_input(self, _source: str = "") -> None:
        self.btn_input.setChecked(True)
        self.stack.setCurrentIndex(1)
        self.input_page.refresh_preferences()

    def _on_open_course(self, course_id: str) -> None:
        self.btn_input.setChecked(True)
        self.stack.setCurrentIndex(1)
        self.input_page.refresh_preferences()
        self.input_page.select_course(course_id)

    def _on_open_settings(self) -> None:
        self.btn_settings.setChecked(True)
        self.stack.setCurrentIndex(5)
        self.settings_page.reload_preferences()

    def _on_open_history(self) -> None:
        self.btn_history.setChecked(True)
        self.stack.setCurrentIndex(4)
        self.history_page.refresh()

    def refresh_sidebar_profile(self) -> None:
        profile = load_preferences().student
        self.sidebar_user_name.setText(profile.full_name.strip() or "Student")
        self.sidebar_user_meta.setText(
            profile.roll_number.strip() or "Complete your profile"
        )

    def _on_settings_saved(self) -> None:
        self.refresh_sidebar_profile()
        self.home_page.refresh_profile()

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
            prompt_text = "\n".join(f"• {q}" for q in questions)
            text, ok = QInputDialog.getMultiLineText(
                self,
                "Optional Experimental Data",
                (
                    "The following details are recommended for this lab report:\n\n"
                    f"{prompt_text}\n\n"
                    "Tip: If you do not have specific measurements or trial data,\n"
                    "leave this blank and click OK (or Cancel) to let the AI generate\n"
                    "realistic simulated observations and benchmarks automatically."
                ),
                "",
            )
            if ok and text.strip():
                self.worker.configure_resume(self.worker.thread_id, {"provided_data": text.strip()})
                self.worker.start()
            else:
                self.worker.configure_resume(
                    self.worker.thread_id,
                    {"provided_data": "Simulate standard realistic observations."},
                )
                self.worker.start()

        elif interrupt_type == "human_review":
            self.btn_review.setChecked(True)
            self.stack.setCurrentIndex(3)
            self.review_page.load_review_data(
                data.get("report", {}),
                data.get("evaluation", {}),
                data.get("telemetry", {}),
            )

    def _on_review_decision(self, decision: HumanDecision) -> None:
        self.btn_processing.setChecked(True)
        self.stack.setCurrentIndex(2)
        self.processing_page.progress_log.status_label.setText(
            "Applying review decision..."
        )

        self.worker.configure_resume(self.worker.thread_id, decision.model_dump())
        self.worker.start()

    def _on_edit_requested(self, assignment_id: int) -> None:
        self.btn_input.setChecked(True)
        self.stack.setCurrentIndex(1)
        self.input_page.refresh_preferences()
        if not self.input_page.load_assignment(assignment_id):
            self._on_open_history()

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
        self.processing_page.progress_log.log_box.append(f"[ERROR] {error_message}")
        self.processing_page.progress_log.status_label.setText("Workflow failed")
        QMessageBox.critical(
            self,
            "Workflow Error",
            f"The workflow encountered an error:\n\n{error_message}",
        )
