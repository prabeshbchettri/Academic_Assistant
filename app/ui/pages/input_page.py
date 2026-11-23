from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from integrations.classroom.client import build_classroom_service, list_courses, list_coursework
from integrations.gmail.client import (
    build_gmail_service,
    get_message_content_and_attachments,
    search_messages,
)
from integrations.google_auth import is_authenticated
from models.assignment import RawInput, SourceType


class InputPage(QWidget):
    start_generation = Signal(RawInput, str)  # raw_input, category_name

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("Select Assignment Input Source")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #1B365D;")
        layout.addWidget(title)

        # Tabs: Google Classroom first as primary student workflow
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self._setup_classroom_tab()
        self._setup_manual_tab()
        self._setup_file_tab()
        self._setup_gmail_tab()

        # Category and Start Bar
        bottom_bar = QFrame()
        bottom_bar.setProperty("class", "Card")
        b_layout = QHBoxLayout(bottom_bar)

        b_layout.addWidget(QLabel("Target Category:"))
        self.category_combo = QComboBox()
        self.category_combo.addItem("Auto-Detect (Recommended)", "")
        self.category_combo.addItem("Academic Assignment", "assignment")
        self.category_combo.addItem("Initial Lab Report", "initial_lab")
        self.category_combo.addItem("Final Comprehensive Lab", "final_lab")
        b_layout.addWidget(self.category_combo)

        b_layout.addStretch()

        self.start_button = QPushButton("Start Preparation & Generation")
        self.start_button.setObjectName("PrimaryButton")
        self.start_button.clicked.connect(self._on_start_clicked)
        b_layout.addWidget(self.start_button)

        layout.addWidget(bottom_bar)

    def _setup_manual_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        layout.addWidget(QLabel("Assignment Title:"))
        self.manual_title = QLineEdit()
        self.manual_title.setPlaceholderText("e.g. Experiment 3: RC Circuit Analysis")
        layout.addWidget(self.manual_title)

        layout.addWidget(QLabel("Course Name (Optional):"))
        self.manual_course = QLineEdit()
        self.manual_course.setPlaceholderText("e.g. Physics 201")
        layout.addWidget(self.manual_course)

        layout.addWidget(QLabel("Assignment Prompt / Guidelines / Problem Description:"))
        self.manual_text = QTextEdit()
        self.manual_text.setPlaceholderText(
            "Paste the assignment requirements, questions, or lab instructions here..."
        )
        layout.addWidget(self.manual_text)

        self.tabs.addTab(tab, "Manual Input")

    def _setup_file_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        layout.addWidget(QLabel("Upload Academic Document (PDF, DOCX, TXT):"))
        pick_btn = QPushButton("Select File...")
        pick_btn.setObjectName("SecondaryButton")
        pick_btn.clicked.connect(self._on_pick_file)
        layout.addWidget(pick_btn)

        self.file_label = QLabel("No file selected.")
        self.file_label.setStyleSheet("color: #64748B; font-style: italic;")
        layout.addWidget(self.file_label)

        layout.addWidget(QLabel("Additional Notes / Observations:"))
        self.file_notes = QTextEdit()
        self.file_notes.setPlaceholderText(
            "Provide any specific data measurements or notes to accompany the file..."
        )
        layout.addWidget(self.file_notes)

        self.selected_file_path: Path | None = None
        self.tabs.addTab(tab, "Local File")

    def _setup_classroom_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)

        header_layout = QHBoxLayout()
        self.classroom_auth_btn = QPushButton("Connect Google Classroom")
        self.classroom_auth_btn.setObjectName("PrimaryButton")
        self.classroom_auth_btn.clicked.connect(self._load_classroom_courses)
        header_layout.addWidget(self.classroom_auth_btn)

        header_layout.addWidget(QLabel("Select Enrolled Class:"))
        self.course_combo = QComboBox()
        self.course_combo.setMinimumWidth(250)
        self.course_combo.currentIndexChanged.connect(self._on_course_selected)
        header_layout.addWidget(self.course_combo)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        layout.addWidget(QLabel("Assignments in this Class:"))
        self.coursework_list = QListWidget()
        self.coursework_list.currentRowChanged.connect(self._on_coursework_selected)
        layout.addWidget(self.coursework_list)

        # Assignment details card
        self.assignment_preview_card = QFrame()
        self.assignment_preview_card.setProperty("class", "Card")
        preview_layout = QVBoxLayout(self.assignment_preview_card)
        
        self.selected_assignment_title = QLabel(
            "Select an assignment above to preview instructions."
        )
        self.selected_assignment_title.setStyleSheet(
            "font-weight: bold; font-size: 14px; color: #1B365D;"
        )
        preview_layout.addWidget(self.selected_assignment_title)

        self.selected_assignment_desc = QTextEdit()
        self.selected_assignment_desc.setReadOnly(True)
        self.selected_assignment_desc.setMaximumHeight(100)
        self.selected_assignment_desc.setPlaceholderText(
            "Assignment instructions from your teacher will appear here..."
        )
        preview_layout.addWidget(self.selected_assignment_desc)

        build_btn_layout = QHBoxLayout()
        build_btn_layout.addStretch()
        self.quick_build_btn = QPushButton("Build Document for Selected Assignment")
        self.quick_build_btn.setObjectName("PrimaryButton")
        self.quick_build_btn.clicked.connect(self._on_start_clicked)
        build_btn_layout.addWidget(self.quick_build_btn)
        preview_layout.addLayout(build_btn_layout)

        layout.addWidget(self.assignment_preview_card)

        self.classroom_courses: list[dict] = []
        self.classroom_items: list[dict] = []
        self.tabs.addTab(tab, "Google Classroom")

        # Auto-connect if credentials already saved
        if is_authenticated():
            self.classroom_auth_btn.setText("Refresh Classes")
            self.classroom_auth_btn.setObjectName("SecondaryButton")
            self._load_classroom_courses(silent=True)

    def _setup_gmail_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        search_layout = QHBoxLayout()
        self.gmail_query = QLineEdit("assignment OR lab OR coursework")
        search_layout.addWidget(self.gmail_query)

        search_btn = QPushButton("Search Emails")
        search_btn.setObjectName("SecondaryButton")
        search_btn.clicked.connect(self._search_gmail)
        search_layout.addWidget(search_btn)
        layout.addLayout(search_layout)

        self.gmail_list = QListWidget()
        layout.addWidget(self.gmail_list)

        self.gmail_messages: list[dict] = []
        self.tabs.addTab(tab, "Gmail")

    def _on_pick_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Assignment Document",
            "",
            "Documents (*.pdf *.docx *.txt *.md)",
        )
        if path:
            self.selected_file_path = Path(path)
            self.file_label.setText(f"Selected: {self.selected_file_path.name}")

    def _load_classroom_courses(self, silent: bool = False) -> None:
        try:
            service = build_classroom_service()
            self.classroom_courses = list_courses(service)
            self.course_combo.blockSignals(True)
            self.course_combo.clear()
            for c in self.classroom_courses:
                self.course_combo.addItem(c.get("name", "Unnamed Course"), c.get("id"))
            self.course_combo.blockSignals(False)
            self.classroom_auth_btn.setText("Refresh Classes")
            self.classroom_auth_btn.setObjectName("SecondaryButton")

            if self.classroom_courses:
                self._on_course_selected(0)

            if not silent:
                QMessageBox.information(
                    self,
                    "Google Classroom",
                    f"Found {len(self.classroom_courses)} active courses.",
                )
        except Exception as exc:
            if not silent:
                QMessageBox.critical(
                    self,
                    "Google Auth Error",
                    f"Could not connect to Google Classroom: {exc}",
                )

    def _on_course_selected(self, index: int) -> None:
        if index < 0 or not self.classroom_courses:
            return
        course_id = self.classroom_courses[index].get("id")
        try:
            service = build_classroom_service()
            self.classroom_items = list_coursework(service, course_id)
            self.coursework_list.clear()
            for item in self.classroom_items:
                self.coursework_list.addItem(
                    f"{item.get('title', 'Untitled')} (ID: {item.get('id')})"
                )
            if self.classroom_items:
                self.coursework_list.setCurrentRow(0)
        except Exception:
            self.coursework_list.clear()

    def select_course(self, course_id: str) -> None:
        self.tabs.setCurrentIndex(0)
        if not self.classroom_courses:
            self._load_classroom_courses(silent=True)
        for index, course in enumerate(self.classroom_courses):
            if str(course.get("id")) == str(course_id):
                self.course_combo.setCurrentIndex(index)
                self._on_course_selected(index)
                return
        self._load_classroom_courses(silent=True)
        for index, course in enumerate(self.classroom_courses):
            if str(course.get("id")) == str(course_id):
                self.course_combo.setCurrentIndex(index)
                self._on_course_selected(index)
                return

    def _on_coursework_selected(self, row: int) -> None:
        if 0 <= row < len(self.classroom_items):
            item = self.classroom_items[row]
            title = item.get("title", "Untitled Assignment")
            desc = item.get("description", "(No written description provided by teacher)")
            self.selected_assignment_title.setText(f"Assignment: {title}")
            self.selected_assignment_desc.setPlainText(desc)

    def _search_gmail(self) -> None:
        try:
            service = build_gmail_service()
            query = self.gmail_query.text()
            self.gmail_messages = search_messages(service, query=query)
            self.gmail_list.clear()
            for msg in self.gmail_messages:
                self.gmail_list.addItem(f"{msg['subject']} - {msg['sender']} ({msg['date']})")
        except Exception as exc:
            QMessageBox.critical(self, "Gmail Error", f"Could not search Gmail: {exc}")

    def _on_start_clicked(self) -> None:
        current_tab_idx = self.tabs.currentIndex()
        cat = self.category_combo.currentData() or ""

        if current_tab_idx == 0:  # Classroom
            row = self.coursework_list.currentRow()
            if row < 0 or not self.classroom_items:
                QMessageBox.warning(
                    self,
                    "Missing Input",
                    "Please select an assignment from the list.",
                )
                return
            item = self.classroom_items[row]
            title = item.get("title", "Classroom Assignment")
            description = item.get("description", "")
            raw = RawInput(
                source_type=SourceType.CLASSROOM,
                title=title,
                raw_text=description or title,
                external_id=item.get("id"),
            )
            self.start_generation.emit(raw, cat)

        elif current_tab_idx == 1:  # Manual
            text = self.manual_text.toPlainText().strip()
            title = self.manual_title.text().strip()
            course = self.manual_course.text().strip()
            if not text:
                QMessageBox.warning(self, "Missing Input", "Please enter assignment text.")
                return
            raw = RawInput(
                source_type=SourceType.MANUAL,
                title=title,
                raw_text=text,
                course_name=course,
            )
            self.start_generation.emit(raw, cat)

        elif current_tab_idx == 2:  # File
            if not self.selected_file_path:
                QMessageBox.warning(self, "Missing Input", "Please select a document file.")
                return
            notes = self.file_notes.toPlainText().strip()
            raw = RawInput(
                source_type=SourceType.FILE,
                title=self.selected_file_path.stem,
                file_path=str(self.selected_file_path),
                raw_text=notes,
            )
            self.start_generation.emit(raw, cat)

        elif current_tab_idx == 3:  # Gmail
            row = self.gmail_list.currentRow()
            if row < 0 or not self.gmail_messages:
                QMessageBox.warning(self, "Missing Input", "Please select an email message.")
                return
            msg = self.gmail_messages[row]
            try:
                service = build_gmail_service()
                content = get_message_content_and_attachments(service, msg["id"])
                raw = RawInput(
                    source_type=SourceType.GMAIL,
                    title=msg["subject"],
                    raw_text=content["body_text"],
                    external_id=msg["id"],
                )
                self.start_generation.emit(raw, cat)
            except Exception as exc:
                QMessageBox.critical(self, "Error", f"Could not retrieve email contents: {exc}")
