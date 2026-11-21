from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from database.db import get_session
from database.repositories import AssignmentRepository


class HomePage(QWidget):
    navigate_to_input = Signal(str)  # source_tab_name
    resume_assignment = Signal(int)  # assignment_id

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # Hero Banner Card
        hero = QFrame()
        hero.setObjectName("Card")
        hero.setProperty("class", "Card")
        hero_layout = QVBoxLayout(hero)

        title = QLabel("Academic Document Preparation Assistant")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #1B365D;")
        hero_layout.addWidget(title)

        subtitle = QLabel(
            "Prepare publication-grade academic assignments, initial lab reports, and final lab reports.\n"
            "Powered by Google Gemini with deterministic verification and mandatory human review."
        )
        subtitle.setStyleSheet("color: #4A5568; font-size: 14px; line-height: 1.4;")
        hero_layout.addWidget(subtitle)

        # Quick Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        btn_manual = QPushButton("+ New Assignment")
        btn_manual.setObjectName("PrimaryButton")
        btn_manual.clicked.connect(lambda: self.navigate_to_input.emit("manual"))
        btn_layout.addWidget(btn_manual)

        btn_file = QPushButton("Import Local File")
        btn_file.setObjectName("SecondaryButton")
        btn_file.clicked.connect(lambda: self.navigate_to_input.emit("file"))
        btn_layout.addWidget(btn_file)

        btn_classroom = QPushButton("Google Classroom")
        btn_classroom.setObjectName("SecondaryButton")
        btn_classroom.clicked.connect(lambda: self.navigate_to_input.emit("classroom"))
        btn_layout.addWidget(btn_classroom)

        btn_layout.addStretch()
        hero_layout.addLayout(btn_layout)
        layout.addWidget(hero)

        # Recent Assignments Section
        recent_label = QLabel("Recent Assignments")
        recent_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #2D3748;")
        layout.addWidget(recent_label)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Title", "Category", "Status", "Date"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        layout.addWidget(self.table)

    def refresh_recent(self) -> None:
        try:
            with get_session() as session:
                repo = AssignmentRepository(session)
                assignments = repo.list_all(limit=15)

            self.table.setRowCount(len(assignments))
            for row, assign in enumerate(assignments):
                self.table.setItem(row, 0, QTableWidgetItem(str(assign.id)))
                self.table.setItem(row, 1, QTableWidgetItem(assign.title))
                self.table.setItem(row, 2, QTableWidgetItem(assign.category.replace("_", " ").title()))
                self.table.setItem(row, 3, QTableWidgetItem(assign.status.title()))
                date_str = assign.created_at.strftime("%Y-%m-%d %H:%M") if assign.created_at else ""
                self.table.setItem(row, 4, QTableWidgetItem(date_str))
        except Exception:
            pass
