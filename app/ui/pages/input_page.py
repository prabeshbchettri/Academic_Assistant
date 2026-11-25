from __future__ import annotations

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.preferences import load_preferences
from app.ui.widgets.preparation_form import PreparationForm
from app.ui.workers import ClassroomCoursesWorker, ClassroomCourseworkWorker
from database.db import get_session
from database.repositories import AssignmentRepository
from integrations.classroom.client import extract_materials_summary
from integrations.google_auth import is_authenticated
from models.assignment import RawInput, SourceType


class InputPage(QWidget):
    start_generation = Signal(RawInput, str)  # raw_input, category_name

    def __init__(self, parent: QWidget | None = None, auto_load: bool = True):
        super().__init__(parent)
        self.auto_load = auto_load
        self.classroom_courses: list[dict] = []
        self.classroom_items: list[dict] = []
        self._courses_worker: ClassroomCoursesWorker | None = None
        self._coursework_worker: ClassroomCourseworkWorker | None = None
        self._pending_course_id: str | None = None
        self._coursework_course_id: str | None = None
        self._pending_coursework_id: str | None = None
        self.editing_assignment_id: int | None = None
        self.editing_title = ""
        self.editing_raw_text = ""
        self.editing_category = ""
        self.editing_source_type = "classroom"

        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 26, 28, 26)
        outer.setSpacing(16)

        outer.addLayout(self._build_header())

        self.auth_card = self._build_auth_card()
        outer.addWidget(self.auth_card)

        self.workspace = QWidget()
        workspace_layout = QVBoxLayout(self.workspace)
        workspace_layout.setContentsMargins(0, 0, 0, 0)
        workspace_layout.setSpacing(14)
        workspace_layout.addWidget(self._build_editing_banner())
        workspace_layout.addWidget(self._build_class_bar())

        body = QHBoxLayout()
        body.setSpacing(16)
        body.addWidget(self._build_assignment_panel())
        body.addLayout(self._build_preparation_panel(), 1)
        workspace_layout.addLayout(body, 1)
        outer.addWidget(self.workspace, 1)

        self.form = PreparationForm()
        self.form_scroll.setWidget(self.form)

        if auto_load and is_authenticated():
            self._load_courses(silent=True)
        else:
            self._show_disconnected()

    def _build_header(self) -> QHBoxLayout:
        header = QHBoxLayout()
        text = QVBoxLayout()
        text.setSpacing(3)

        title = QLabel("Prepare an assignment")
        title.setObjectName("PageTitle")
        text.addWidget(title)

        subtitle = QLabel(
            "Choose a class, pick the assignment, confirm your details, then start preparing."
        )
        subtitle.setObjectName("PageSubtitle")
        text.addWidget(subtitle)
        header.addLayout(text, 1)

        self.sync_status = QLabel("Not connected")
        self.sync_status.setObjectName("Muted")
        header.addWidget(self.sync_status, 0, Qt.AlignmentFlag.AlignTop)
        return header

    def _build_auth_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("AuthCard")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(18)

        copy = QVBoxLayout()
        copy.setSpacing(5)
        title = QLabel("Connect Google Classroom")
        title.setObjectName("CardTitle")
        copy.addWidget(title)
        subtitle = QLabel(
            "Sign in with your student account to load your enrolled classes and assignments."
        )
        subtitle.setObjectName("Muted")
        subtitle.setWordWrap(True)
        copy.addWidget(subtitle)
        layout.addLayout(copy, 1)

        self.connect_btn = QPushButton("Connect Classroom")
        self.connect_btn.setObjectName("PrimaryButton")
        self.connect_btn.clicked.connect(lambda: self._load_courses())
        layout.addWidget(self.connect_btn)
        return card

    def _build_editing_banner(self) -> QFrame:
        self.editing_banner = QFrame()
        self.editing_banner.setObjectName("ConnectionBar")
        layout = QHBoxLayout(self.editing_banner)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(10)

        self.editing_label = QLabel("")
        self.editing_label.setObjectName("ConnectionLabel")
        self.editing_label.setWordWrap(True)
        layout.addWidget(self.editing_label, 1)

        cancel = QPushButton("Cancel edit")
        cancel.setObjectName("GhostButton")
        cancel.clicked.connect(self._cancel_edit)
        layout.addWidget(cancel)
        self.editing_banner.setVisible(False)
        return self.editing_banner

    def _build_class_bar(self) -> QFrame:
        bar = QFrame()
        bar.setProperty("class", "Card")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        label = QLabel("Class")
        label.setObjectName("FieldLabel")
        layout.addWidget(label)

        self.course_combo = QComboBox()
        self.course_combo.setMinimumWidth(300)
        self.course_combo.currentIndexChanged.connect(self._on_course_selected)
        layout.addWidget(self.course_combo, 1)

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setObjectName("SecondaryButton")
        self.refresh_btn.clicked.connect(lambda: self._load_courses())
        layout.addWidget(self.refresh_btn)

        self.coursework_status = QLabel("")
        self.coursework_status.setObjectName("Muted")
        layout.addWidget(self.coursework_status)
        return bar

    def _build_assignment_panel(self) -> QFrame:
        panel = QFrame()
        panel.setProperty("class", "Card")
        panel.setFixedWidth(340)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        heading = QLabel("Assignments")
        heading.setObjectName("CardTitle")
        layout.addWidget(heading)

        self.assignment_hint = QLabel("Select a class to load assignments.")
        self.assignment_hint.setObjectName("Muted")
        self.assignment_hint.setWordWrap(True)
        layout.addWidget(self.assignment_hint)

        self.assignment_list = QListWidget()
        self.assignment_list.setObjectName("AssignmentList")
        self.assignment_list.currentRowChanged.connect(self._on_assignment_selected)
        layout.addWidget(self.assignment_list, 1)
        return panel

    def _build_preparation_panel(self) -> QVBoxLayout:
        column = QVBoxLayout()
        column.setSpacing(12)

        preview = QFrame()
        preview.setProperty("class", "Card")
        preview_layout = QVBoxLayout(preview)
        preview_layout.setContentsMargins(18, 14, 18, 14)
        preview_layout.setSpacing(6)

        preview_header = QHBoxLayout()
        self.assignment_title = QLabel("No assignment selected")
        self.assignment_title.setObjectName("CardTitle")
        preview_header.addWidget(self.assignment_title, 1)

        self.open_link_btn = QPushButton("Open in Classroom")
        self.open_link_btn.setObjectName("GhostButton")
        self.open_link_btn.setVisible(False)
        self.open_link_btn.clicked.connect(self._open_selected_link)
        preview_header.addWidget(self.open_link_btn)
        preview_layout.addLayout(preview_header)

        self.assignment_description = QTextEdit()
        self.assignment_description.setReadOnly(True)
        self.assignment_description.setMaximumHeight(88)
        self.assignment_description.setPlaceholderText(
            "Teacher instructions for the selected assignment will appear here."
        )
        preview_layout.addWidget(self.assignment_description)
        column.addWidget(preview)

        self.form_scroll = QScrollArea()
        self.form_scroll.setWidgetResizable(True)
        self.form_scroll.setFrameShape(QFrame.Shape.NoFrame)
        column.addWidget(self.form_scroll, 1)

        action_bar = QFrame()
        action_bar.setProperty("class", "Card")
        action_layout = QHBoxLayout(action_bar)
        action_layout.setContentsMargins(16, 12, 16, 12)

        hint = QLabel("Everything can be adjusted before generation starts.")
        hint.setObjectName("Muted")
        action_layout.addWidget(hint)
        action_layout.addStretch()

        self.start_button = QPushButton("Start preparing")
        self.start_button.setObjectName("PrimaryButton")
        self.start_button.clicked.connect(self._on_start_clicked)
        action_layout.addWidget(self.start_button)
        column.addWidget(action_bar)
        return column

    def refresh_preferences(self) -> None:
        self.form.load_preferences(load_preferences())

    def load_assignment(self, assignment_id: int) -> bool:
        with get_session() as session:
            record = AssignmentRepository(session).get_by_id(assignment_id)
            if record is None:
                QMessageBox.warning(
                    self,
                    "Assignment not found",
                    "The selected document could not be loaded.",
                )
                return False
            self.editing_assignment_id = record.id
            self.editing_title = record.title
            self.editing_raw_text = record.raw_text or record.title
            self.editing_category = record.category or ""
            self.editing_source_type = record.source_type or "classroom"

        self.auth_card.setVisible(False)
        self.workspace.setVisible(True)
        self.sync_status.setText("Editing saved document")
        self.assignment_title.setText(f"Editing: {self.editing_title}")
        self.assignment_description.setPlainText(self.editing_raw_text)
        self.open_link_btn.setVisible(False)
        self.editing_label.setText(
            f"Editing “{self.editing_title}”. Adjust the details below, then "
            "generate a revised version."
        )
        self.editing_banner.setVisible(True)
        self.start_button.setText("Generate revised version")
        self.form.title_input.setText(self.editing_title)
        self.form.course_input.clear()
        return True

    def _cancel_edit(self) -> None:
        self._clear_edit_state()
        if is_authenticated():
            self._load_courses(silent=True)
        else:
            self._show_disconnected()

    def _clear_edit_state(self) -> None:
        self.editing_assignment_id = None
        self.editing_title = ""
        self.editing_raw_text = ""
        self.editing_category = ""
        self.editing_source_type = "classroom"
        self.editing_banner.setVisible(False)
        self.start_button.setText("Start preparing")

    def _show_disconnected(self) -> None:
        if self.editing_assignment_id is not None:
            self.auth_card.setVisible(False)
            self.workspace.setVisible(True)
            self.sync_status.setText("Editing saved document")
            return
        # Keep the preparation form usable for local files/manual prompts even offline
        self.auth_card.setVisible(True)
        self.workspace.setVisible(True)
        self.sync_status.setText("Offline / Local mode")
        self.assignment_hint.setText(
            "Connect Google Classroom above, or fill details / attach a local PDF on the right."
        )
        self.connect_btn.setEnabled(True)
        self.connect_btn.setText("Connect Classroom")

    def _load_courses(self, silent: bool = False) -> None:
        if self._courses_worker is not None and self._courses_worker.isRunning():
            return

        if not is_authenticated():
            self._show_disconnected()
            if not silent:
                self._connect_google()
            return

        self.connect_btn.setEnabled(False)
        self.connect_btn.setText("Connecting…")
        self.refresh_btn.setEnabled(False)
        self.sync_status.setText("Loading classes…")
        self.course_combo.clear()
        self.assignment_list.clear()
        self.assignment_hint.setText("Loading assignments…")

        worker = ClassroomCoursesWorker(self)
        worker.courses_ready.connect(self._on_courses_ready)
        worker.error.connect(self._on_courses_error)
        worker.finished.connect(self._on_courses_finished)
        self._courses_worker = worker
        worker.start()

    def _connect_google(self) -> None:
        self.connect_btn.setEnabled(False)
        self.connect_btn.setText("Waiting for browser…")
        try:
            from integrations.classroom.client import build_classroom_service

            build_classroom_service()
        except Exception as exc:
            self.connect_btn.setEnabled(True)
            self.connect_btn.setText("Connect Classroom")
            QMessageBox.critical(
                self,
                "Google Authentication",
                f"Could not connect to Google Classroom:\n\n{exc}",
            )
            return
        self.connect_btn.setEnabled(True)
        self.connect_btn.setText("Connect Classroom")
        self._load_courses(silent=True)

    def _on_courses_ready(self, courses: list[dict]) -> None:
        self.classroom_courses = courses
        self.auth_card.setVisible(False)
        self.workspace.setVisible(True)

        self.course_combo.blockSignals(True)
        self.course_combo.clear()
        for course in courses:
            self.course_combo.addItem(course.get("name", "Unnamed Course"), course.get("id"))
        self.course_combo.blockSignals(False)

        self.sync_status.setText(f"Connected — {len(courses)} class(es)")
        if not courses:
            self.assignment_hint.setText(
                "No active classes found. Join or accept your Classroom invitations first."
            )
            return
        if self.editing_assignment_id is not None:
            return

        target = self._pending_course_id
        self._pending_course_id = None
        index = 0
        if target:
            for candidate, course in enumerate(courses):
                if str(course.get("id")) == str(target):
                    index = candidate
                    break
        self.course_combo.setCurrentIndex(index)
        self._on_course_selected(index)

    def _on_courses_error(self, message: str) -> None:
        self.sync_status.setText("Connection failed")
        self.assignment_hint.setText("Could not load classes. Tap Refresh to retry.")
        self.assignment_list.clear()
        self._show_disconnected()
        self.sync_status.setText("Connection failed")
        self.sync_status.setToolTip(message)

    def _on_courses_finished(self) -> None:
        self.connect_btn.setEnabled(True)
        self.connect_btn.setText("Connect Classroom")
        self.refresh_btn.setEnabled(True)
        self._courses_worker = None

    def _on_course_selected(self, index: int) -> None:
        if index < 0 or index >= len(self.classroom_courses):
            return
        course = self.classroom_courses[index]
        course_id = str(course.get("id", ""))
        self.assignment_list.clear()
        self.assignment_hint.setText("Loading assignments…")
        self.assignment_title.setText("Loading…")
        self.assignment_description.clear()
        self.open_link_btn.setVisible(False)

        if self._coursework_worker is not None and self._coursework_worker.isRunning():
            self._pending_coursework_id = course_id
            return

        self._coursework_course_id = course_id
        worker = ClassroomCourseworkWorker(course_id, self)
        worker.coursework_ready.connect(self._on_coursework_ready)
        worker.error.connect(self._on_coursework_error)
        worker.finished.connect(self._on_coursework_finished)
        self._coursework_worker = worker
        worker.start()

    def _on_coursework_ready(self, items: list[dict]) -> None:
        current = str(self._current_course().get("id", ""))
        if self._coursework_course_id and current != self._coursework_course_id:
            return
        self.classroom_items = items
        self.assignment_list.clear()
        if not items:
            self.assignment_hint.setText(
                "No published assignments in this class yet."
            )
            return

        self.assignment_hint.setText(f"{len(items)} assignment(s)")
        for item in items:
            label = item.get("title", "Untitled Assignment")
            due = self._format_due(item.get("dueDate"))
            if due:
                label = f"{label}\nDue {due}"
            list_item = QListWidgetItem(label)
            list_item.setData(Qt.ItemDataRole.UserRole, item.get("id"))
            self.assignment_list.addItem(list_item)
        self.assignment_list.setCurrentRow(0)

    def _on_coursework_error(self, message: str) -> None:
        self.classroom_items = []
        self.assignment_list.clear()
        self.assignment_hint.setText("Could not load assignments for this class.")
        self.assignment_hint.setToolTip(message)

    def _on_coursework_finished(self) -> None:
        self._coursework_worker = None
        pending = self._pending_coursework_id
        self._pending_coursework_id = None
        if pending and pending != str(self._current_course().get("id", "")):
            self._on_course_selected(self.course_combo.currentIndex())

    def _on_assignment_selected(self, row: int) -> None:
        if not (0 <= row < len(self.classroom_items)):
            return
        if self.editing_assignment_id is not None:
            self._clear_edit_state()
        item = self.classroom_items[row]
        title = item.get("title", "Untitled Assignment")
        description = item.get("description", "")
        self.assignment_title.setText(title)
        self.assignment_description.setPlainText(
            description or "No written description provided by the teacher."
        )
        link = item.get("alternateLink")
        self.open_link_btn.setVisible(bool(link))
        course = self._current_course()
        self.form.set_assignment(title, course.get("name"))
        self.sync_status.setToolTip("")

    def _current_course(self) -> dict:
        index = self.course_combo.currentIndex()
        if 0 <= index < len(self.classroom_courses):
            return self.classroom_courses[index]
        return {}

    def _open_selected_link(self) -> None:
        row = self.assignment_list.currentRow()
        if 0 <= row < len(self.classroom_items):
            link = self.classroom_items[row].get("alternateLink")
            if link:
                QDesktopServices.openUrl(QUrl(link))

    def select_course(self, course_id: str) -> None:
        self._pending_course_id = str(course_id)
        if not is_authenticated():
            self._show_disconnected()
            return
        if not self.classroom_courses:
            self._load_courses(silent=True)
            return
        for index, course in enumerate(self.classroom_courses):
            if str(course.get("id")) == str(course_id):
                self.course_combo.setCurrentIndex(index)
                self._on_course_selected(index)
                return
        self._load_courses(silent=True)

    def _on_start_clicked(self) -> None:
        error = self.form.validate()
        if error:
            QMessageBox.warning(self, "Missing details", error)
            return

        if self.editing_assignment_id is not None:
            try:
                source_type = SourceType(self.editing_source_type)
            except ValueError:
                source_type = SourceType.CLASSROOM
            raw = RawInput(
                source_type=source_type,
                title=self.form.title_input.text().strip() or self.editing_title,
                raw_text=self.editing_raw_text,
                metadata={"editing_assignment_id": self.editing_assignment_id},
            )
            prepared, category = self.form.apply_to_raw(raw)
            fallback_category = self.editing_category
            self._clear_edit_state()
            self.start_generation.emit(prepared, category or fallback_category)
            return

        row = self.assignment_list.currentRow()
        if row < 0 or row >= len(self.classroom_items):
            # Support manual/local-file preparation when no Classroom assignment is picked
            title = self.form.title_input.text().strip()
            notes = self.form.extra_notes.toPlainText().strip()
            local_file = self.form.assignment_file_input.text().strip()
            if not (notes or local_file):
                QMessageBox.warning(
                    self,
                    "Assignment details needed",
                    "Choose a Classroom assignment, attach a local PDF/DOCX/TXT, "
                    "or add instructions in the notes box.",
                )
                return
            raw = RawInput(
                source_type=SourceType.FILE if local_file else SourceType.MANUAL,
                title=title,
                raw_text=notes or title,
                file_path=local_file or None,
                course_name=self.form.course_input.text().strip() or None,
            )
            prepared, category = self.form.apply_to_raw(raw)
            self.start_generation.emit(prepared, category)
            return

        item = self.classroom_items[row]
        course = self._current_course()
        title = item.get("title", "Classroom Assignment")
        description = item.get("description", "")
        materials_text = extract_materials_summary(item)
        combined_text = "\n\n".join(p for p in (description, materials_text) if p).strip()
        raw = RawInput(
            source_type=SourceType.CLASSROOM,
            title=title,
            raw_text=combined_text or title,
            course_name=course.get("name"),
            external_id=item.get("id"),
            metadata={
                "classroom": {
                    "course_id": course.get("id"),
                    "course_name": course.get("name"),
                    "coursework_id": item.get("id"),
                    "alternate_link": item.get("alternateLink"),
                    "due_date": item.get("dueDate"),
                }
            },
        )
        prepared, category = self.form.apply_to_raw(raw)
        self.start_generation.emit(prepared, category)

    @staticmethod
    def _format_due(due: dict | None) -> str:
        if not due:
            return ""
        year = due.get("year")
        month = due.get("month")
        day = due.get("day")
        if year and month and day:
            return f"{year:04d}-{month:02d}-{day:02d}"
        return ""
