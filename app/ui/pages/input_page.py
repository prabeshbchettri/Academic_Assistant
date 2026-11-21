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

        # Tabs for 4 sources
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self._setup_manual_tab()
        self._setup_file_tab()
        self._setup_classroom_tab()
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
        l = QVBoxLayout(tab)

        l.addWidget(QLabel("Assignment Title:"))
        self.manual_title = QLineEdit()
        self.manual_title.setPlaceholderText("e.g. Experiment 3: RC Circuit Analysis")
        l.addWidget(self.manual_title)

        l.addWidget(QLabel("Course Name (Optional):"))
        self.manual_course = QLineEdit()
        self.manual_course.setPlaceholderText("e.g. Physics 201")
        l.addWidget(self.manual_course)

        l.addWidget(QLabel("Assignment Prompt / Guidelines / Problem Description:"))
        self.manual_text = QTextEdit()
        self.manual_text.setPlaceholderText("Paste the assignment requirements, questions, or lab instructions here...")
        l.addWidget(self.manual_text)

        self.tabs.addTab(tab, "Manual Input")

    def _setup_file_tab(self) -> None:
        tab = QWidget()
        l = QVBoxLayout(tab)

        l.addWidget(QLabel("Upload Academic Document (PDF, DOCX, TXT):"))
        pick_btn = QPushButton("Select File...")
        pick_btn.setObjectName("SecondaryButton")
        pick_btn.clicked.connect(self._on_pick_file)
        l.addWidget(pick_btn)

        self.file_label = QLabel("No file selected.")
        self.file_label.setStyleSheet("color: #64748B; font-style: italic;")
        l.addWidget(self.file_label)

        l.addWidget(QLabel("Additional Notes / Observations:"))
        self.file_notes = QTextEdit()
        self.file_notes.setPlaceholderText("Provide any specific data measurements or notes to accompany the file...")
        l.addWidget(self.file_notes)

        self.selected_file_path: Path | None = None
        self.tabs.addTab(tab, "Local File")

    def _setup_classroom_tab(self) -> None:
        tab = QWidget()
        l = QVBoxLayout(tab)

        header_layout = QHBoxLayout()
        self.classroom_auth_btn = QPushButton("Connect Google Account")
        self.classroom_auth_btn.setObjectName("SecondaryButton")
        self.classroom_auth_btn.clicked.connect(self._load_classroom_courses)
        header_layout.addWidget(self.classroom_auth_btn)

        self.course_combo = QComboBox()
        self.course_combo.currentIndexChanged.connect(self._on_course_selected)
        header_layout.addWidget(self.course_combo)
        header_layout.addStretch()
        l.addLayout(header_layout)

        l.addWidget(QLabel("Coursework / Assignments:"))
        self.coursework_list = QListWidget()
        l.addWidget(self.coursework_list)

        self.classroom_courses: list[dict] = []
        self.classroom_items: list[dict] = []
        self.tabs.addTab(tab, "Google Classroom")

    def _setup_gmail_tab(self) -> None:
        tab = QWidget()
        l = QVBoxLayout(tab)

        search_layout = QHBoxLayout()
        self.gmail_query = QLineEdit("assignment OR lab OR coursework")
        search_layout.addWidget(self.gmail_query)

        search_btn = QPushButton("Search Emails")
        search_btn.setObjectName("SecondaryButton")
        search_btn.clicked.connect(self._search_gmail)
        search_layout.addWidget(search_btn)
        l.addLayout(search_layout)

        self.gmail_list = QListWidget()
        l.addWidget(self.gmail_list)

        self.gmail_messages: list[dict] = []
        self.tabs.addTab(tab, "Gmail")

    def _on_pick_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select Assignment Document", "", "Documents (*.pdf *.docx *.txt *.md)")
        if path:
            self.selected_file_path = Path(path)
            self.file_label.setText(f"Selected: {self.selected_file_path.name}")

    def _load_classroom_courses(self) -> None:
        try:
            service = build_classroom_service()
            self.classroom_courses = list_courses(service)
            self.course_combo.clear()
            for c in self.classroom_courses:
                self.course_combo.addItem(c.get("name", "Unnamed Course"), c.get("id"))
            QMessageBox.information(self, "Google Classroom", f"Found {len(self.classroom_courses)} active courses.")
        except Exception as exc:
            QMessageBox.critical(self, "Google Auth Error", f"Could not connect to Google Classroom: {exc}")

    def _on_course_selected(self, index: int) -> None:
        if index < 0 or not self.classroom_courses:
            return
        course_id = self.classroom_courses[index].get("id")
        try:
            service = build_classroom_service()
            self.classroom_items = list_coursework(service, course_id)
            self.coursework_list.clear()
            for item in self.classroom_items:
                self.coursework_list.addItem(f"{item.get('title', 'Untitled')} (ID: {item.get('id')})")
        except Exception:
            self.coursework_list.clear()

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

        if current_tab_idx == 0:  # Manual
            text = self.manual_text.toPlainText().strip()
            title = self.manual_title.text().strip()
            course = self.manual_course.text().strip()
            if not text:
                QMessageBox.warning(self, "Missing Input", "Please enter assignment text.")
                return
            raw = RawInput(source_type=SourceType.MANUAL, title=title, raw_text=text, course_name=course)
            self.start_generation.emit(raw, cat)

        elif current_tab_idx == 1:  # File
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

        elif current_tab_idx == 2:  # Classroom
            row = self.coursework_list.currentRow()
            if row < 0 or not self.classroom_items:
                QMessageBox.warning(self, "Missing Input", "Please select a coursework item.")
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
