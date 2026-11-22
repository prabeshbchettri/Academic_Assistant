from __future__ import annotations

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.preferences import is_profile_complete, load_preferences
from app.ui.widgets.course_card import CourseCard
from app.ui.workers import ClassroomCoursesWorker
from database.db import get_session
from database.repositories import AssignmentRepository
from integrations.google_auth import is_authenticated


class HomePage(QWidget):
    open_input = Signal(str)
    open_course = Signal(str)
    open_settings = Signal()
    open_history = Signal()

    def __init__(self, parent: QWidget | None = None, auto_sync: bool = True):
        super().__init__(parent)
        self.auto_sync = auto_sync
        self.courses: list[dict] = []
        self._courses_worker: ClassroomCoursesWorker | None = None

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
        layout.setSpacing(20)

        layout.addLayout(self._build_header())
        layout.addLayout(self._build_quick_actions())
        layout.addWidget(self._build_auth_card())
        layout.addWidget(self._build_connection_bar())
        layout.addLayout(self._build_stats())

        self.courses_section = QWidget()
        courses_layout = QVBoxLayout(self.courses_section)
        courses_layout.setContentsMargins(0, 0, 0, 0)
        courses_layout.setSpacing(12)

        courses_header = QHBoxLayout()
        courses_title = QLabel("Your classes")
        courses_title.setObjectName("SectionTitle")
        courses_header.addWidget(courses_title)
        courses_header.addStretch()
        self.sync_hint = QLabel("")
        self.sync_hint.setObjectName("Muted")
        courses_header.addWidget(self.sync_hint)
        courses_layout.addLayout(courses_header)

        self.course_container = QWidget()
        self.course_grid = QGridLayout(self.course_container)
        self.course_grid.setContentsMargins(0, 0, 0, 0)
        self.course_grid.setHorizontalSpacing(14)
        self.course_grid.setVerticalSpacing(14)
        courses_layout.addWidget(self.course_container)
        layout.addWidget(self.courses_section)

        recent_header = QHBoxLayout()
        recent_title = QLabel("Recent documents")
        recent_title.setObjectName("SectionTitle")
        recent_header.addWidget(recent_title)
        recent_header.addStretch()
        view_all = QPushButton("View all")
        view_all.setObjectName("GhostButton")
        view_all.clicked.connect(lambda: self.open_history.emit())
        recent_header.addWidget(view_all)
        layout.addLayout(recent_header)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Title", "Type", "Status", "Updated"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setMinimumHeight(180)
        layout.addWidget(self.table)
        layout.addStretch()

        self.refresh_profile()
        self.refresh_recent()
        if auto_sync and is_authenticated():
            self.sync_classroom()

    def _build_header(self) -> QHBoxLayout:
        header = QHBoxLayout()
        header.setSpacing(18)

        text_col = QVBoxLayout()
        text_col.setSpacing(4)
        self.greeting = QLabel("Welcome")
        self.greeting.setObjectName("PageTitle")
        text_col.addWidget(self.greeting)

        self.header_subtitle = QLabel("Your Classroom assignments, formatted for submission.")
        self.header_subtitle.setObjectName("PageSubtitle")
        text_col.addWidget(self.header_subtitle)
        header.addLayout(text_col, 1)

        profile = QFrame()
        profile.setObjectName("ProfileChip")
        profile_layout = QHBoxLayout(profile)
        profile_layout.setContentsMargins(12, 10, 12, 10)
        profile_layout.setSpacing(10)

        self.avatar = QLabel("ST")
        self.avatar.setObjectName("Avatar")
        self.avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        profile_layout.addWidget(self.avatar)

        profile_text = QVBoxLayout()
        profile_text.setSpacing(1)
        self.profile_name = QLabel("Student")
        self.profile_name.setObjectName("ProfileName")
        profile_text.addWidget(self.profile_name)
        self.profile_meta = QLabel("Complete your profile")
        self.profile_meta.setObjectName("Muted")
        profile_text.addWidget(self.profile_meta)
        profile_layout.addLayout(profile_text)

        edit = QPushButton("Edit")
        edit.setObjectName("GhostButton")
        edit.clicked.connect(lambda: self.open_settings.emit())
        profile_layout.addWidget(edit)

        header.addWidget(profile, 0, Qt.AlignmentFlag.AlignTop)
        return header

    def _build_quick_actions(self) -> QHBoxLayout:
        actions = QHBoxLayout()
        actions.setSpacing(10)

        classroom = QPushButton("Open Classroom")
        classroom.setObjectName("PrimaryButton")
        classroom.clicked.connect(lambda: self.open_input.emit("classroom"))
        actions.addWidget(classroom)

        manual = QPushButton("New from text")
        manual.setObjectName("SecondaryButton")
        manual.clicked.connect(lambda: self.open_input.emit("manual"))
        actions.addWidget(manual)

        upload = QPushButton("Import file")
        upload.setObjectName("SecondaryButton")
        upload.clicked.connect(lambda: self.open_input.emit("file"))
        actions.addWidget(upload)

        actions.addStretch()
        return actions

    def _build_auth_card(self) -> QFrame:
        self.auth_card = QFrame()
        self.auth_card.setObjectName("AuthCard")
        layout = QHBoxLayout(self.auth_card)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(18)

        copy = QVBoxLayout()
        copy.setSpacing(5)
        title = QLabel("Connect Google Classroom")
        title.setObjectName("CardTitle")
        copy.addWidget(title)
        subtitle = QLabel(
            "Sign in with your student account to see enrolled classes, assignments, "
            "due dates, and teacher instructions."
        )
        subtitle.setObjectName("Muted")
        subtitle.setWordWrap(True)
        copy.addWidget(subtitle)
        layout.addLayout(copy, 1)

        self.connect_btn = QPushButton("Connect Classroom")
        self.connect_btn.setObjectName("PrimaryButton")
        self.connect_btn.clicked.connect(lambda: self.sync_classroom())
        layout.addWidget(self.connect_btn)

        skip = QPushButton("Use without Classroom")
        skip.setObjectName("SecondaryButton")
        skip.clicked.connect(lambda: self.open_input.emit("manual"))
        layout.addWidget(skip)
        return self.auth_card

    def _build_connection_bar(self) -> QFrame:
        self.connection_bar = QFrame()
        self.connection_bar.setObjectName("ConnectionBar")
        layout = QHBoxLayout(self.connection_bar)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(10)

        dot = QLabel("●")
        dot.setObjectName("StatusDot")
        layout.addWidget(dot)

        self.connection_label = QLabel("Connected to Google Classroom")
        self.connection_label.setObjectName("ConnectionLabel")
        layout.addWidget(self.connection_label)
        layout.addStretch()

        self.refresh_btn = QPushButton("Refresh classes")
        self.refresh_btn.setObjectName("GhostButton")
        self.refresh_btn.clicked.connect(lambda: self.sync_classroom())
        layout.addWidget(self.refresh_btn)
        return self.connection_bar

    def _build_stats(self) -> QHBoxLayout:
        stats = QHBoxLayout()
        stats.setSpacing(14)
        self.stat_classes = self._stat_card("Classes", "0", "Enrolled in Classroom")
        self.stat_docs = self._stat_card("Documents", "0", "Generated locally")
        self.stat_profile = self._stat_card("Profile", "Needs details", "Name and roll number")
        stats.addWidget(self.stat_classes[0])
        stats.addWidget(self.stat_docs[0])
        stats.addWidget(self.stat_profile[0])
        return stats

    def _stat_card(self, label: str, value: str, hint: str) -> tuple[QFrame, QLabel, QLabel]:
        card = QFrame()
        card.setObjectName("StatCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(2)

        label_widget = QLabel(label.upper())
        label_widget.setObjectName("StatLabel")
        layout.addWidget(label_widget)

        value_widget = QLabel(value)
        value_widget.setObjectName("StatValue")
        layout.addWidget(value_widget)

        hint_widget = QLabel(hint)
        hint_widget.setObjectName("Muted")
        layout.addWidget(hint_widget)
        return card, value_widget, hint_widget

    def refresh_profile(self) -> None:
        prefs = load_preferences()
        profile = prefs.student
        complete = is_profile_complete(profile)

        name = profile.full_name.strip()
        first_name = name.split(" ")[0] if name else "Student"
        self.greeting.setText(f"Welcome back, {first_name}")
        self.profile_name.setText(profile.full_name.strip() or "Student")
        self.profile_meta.setText(
            profile.roll_number.strip() or "Add your roll number in Settings"
        )
        self.avatar.setText(self._initials(profile.full_name))
        self.stat_profile[1].setText("Ready" if complete else "Needs details")
        self.stat_profile[2].setText(
            profile.roll_number.strip() or "Add name and roll number in Settings"
        )
        self.auth_card.setVisible(not is_authenticated())
        self.connection_bar.setVisible(is_authenticated())
        self.courses_section.setVisible(is_authenticated())

    def refresh_recent(self) -> None:
        try:
            with get_session() as session:
                repo = AssignmentRepository(session)
                assignments = repo.list_all(limit=8)

            self.table.setRowCount(len(assignments))
            for row, assignment in enumerate(assignments):
                self.table.setItem(row, 0, QTableWidgetItem(assignment.title))
                self.table.setItem(
                    row,
                    1,
                    QTableWidgetItem(assignment.category.replace("_", " ").title()),
                )
                self.table.setItem(row, 2, QTableWidgetItem(assignment.status.title()))
                updated = assignment.updated_at or assignment.created_at
                self.table.setItem(
                    row,
                    3,
                    QTableWidgetItem(updated.strftime("%b %d, %H:%M") if updated else ""),
                )
            self.stat_docs[1].setText(str(len(assignments)))
        except Exception:
            self.table.setRowCount(0)

    def sync_classroom(self) -> None:
        if self._courses_worker is not None and self._courses_worker.isRunning():
            return

        self.connect_btn.setEnabled(False)
        self.connect_btn.setText("Connecting…")
        self.refresh_btn.setEnabled(False)
        self.connection_label.setText("Syncing classes from Google Classroom…")
        self.sync_hint.setText("Syncing…")
        self._render_loading_state()

        worker = ClassroomCoursesWorker(self)
        worker.courses_ready.connect(self._on_courses_ready)
        worker.error.connect(self._on_courses_error)
        worker.finished.connect(self._on_courses_worker_finished)
        self._courses_worker = worker
        worker.start()

    def _on_courses_ready(self, courses: list[dict]) -> None:
        self.courses = courses
        self.auth_card.setVisible(False)
        self.connection_bar.setVisible(True)
        self.courses_section.setVisible(True)
        self.connection_label.setText(f"Connected — {len(courses)} active class(es)")
        self.stat_classes[1].setText(str(len(courses)))
        self.sync_hint.setText("Up to date")
        self._render_courses(courses)

    def _on_courses_error(self, message: str) -> None:
        self.auth_card.setVisible(True)
        self.connection_bar.setVisible(False)
        self.courses_section.setVisible(False)
        self.connection_label.setText("Could not load Google Classroom")
        self.sync_hint.setText("Connection failed")
        self._render_courses([])
        self._show_error_hint(message)

    def _on_courses_worker_finished(self) -> None:
        self.connect_btn.setEnabled(True)
        self.connect_btn.setText("Connect Classroom")
        self.refresh_btn.setEnabled(True)
        self._courses_worker = None

    def _render_loading_state(self) -> None:
        self._clear_course_grid()
        loading = QLabel("Loading your classes…")
        loading.setObjectName("EmptyState")
        loading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.course_grid.addWidget(loading, 0, 0, 1, 2)

    def _render_courses(self, courses: list[dict]) -> None:
        self._clear_course_grid()
        if not courses:
            empty = QLabel(
                "No active classes found.\n"
                "Make sure you are signed in with your student account and have accepted "
                "your Classroom invitations."
            )
            empty.setObjectName("EmptyState")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setWordWrap(True)
            self.course_grid.addWidget(empty, 0, 0, 1, 2)
            return

        for index, course in enumerate(courses):
            card = CourseCard(course)
            card.open_course.connect(self.open_course.emit)
            card.open_link.connect(self._open_external_link)
            self.course_grid.addWidget(card, index // 2, index % 2)

    def _clear_course_grid(self) -> None:
        while self.course_grid.count():
            item = self.course_grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _open_external_link(self, url: str) -> None:
        QDesktopServices.openUrl(QUrl(url))

    def _show_error_hint(self, message: str) -> None:
        self.sync_hint.setText("Tap Connect to retry")
        self.sync_hint.setToolTip(message)

    @staticmethod
    def _initials(name: str) -> str:
        parts = [part for part in name.strip().split() if part]
        if not parts:
            return "ST"
        if len(parts) == 1:
            return parts[0][:2].upper()
        return (parts[0][0] + parts[-1][0]).upper()
