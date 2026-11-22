from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class CourseCard(QFrame):
    open_course = Signal(str)
    open_link = Signal(str)

    def __init__(self, course: dict[str, Any], parent: QWidget | None = None):
        super().__init__(parent)
        self.course = course
        self.course_id = str(course.get("id", ""))
        self.setObjectName("CourseCard")
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 16)
        layout.setSpacing(10)

        top = QHBoxLayout()
        name = QLabel(course.get("name", "Untitled class"))
        name.setObjectName("CourseCardTitle")
        name.setWordWrap(True)
        top.addWidget(name, 1)

        state = QLabel(self._friendly_state(course.get("courseState", "")))
        state.setObjectName("Pill")
        top.addWidget(state, 0, Qt.AlignmentFlag.AlignTop)
        layout.addLayout(top)

        section = course.get("section") or course.get("descriptionHeading") or "No section listed"
        section_label = QLabel(section)
        section_label.setObjectName("Muted")
        section_label.setWordWrap(True)
        layout.addWidget(section_label)

        room = course.get("room")
        if room:
            room_label = QLabel(f"Room {room}")
            room_label.setObjectName("Muted")
            layout.addWidget(room_label)

        layout.addStretch()

        actions = QHBoxLayout()
        open_btn = QPushButton("Open class")
        open_btn.setObjectName("PrimaryButton")
        open_btn.clicked.connect(lambda: self.open_course.emit(self.course_id))
        actions.addWidget(open_btn)

        link = course.get("alternateLink")
        if link:
            link_btn = QPushButton("Classroom")
            link_btn.setObjectName("GhostButton")
            link_btn.clicked.connect(lambda: self.open_link.emit(str(link)))
            actions.addWidget(link_btn)

        actions.addStretch()
        layout.addLayout(actions)

    def _friendly_state(self, state: str) -> str:
        return {
            "ACTIVE": "Active",
            "ARCHIVED": "Archived",
            "PROVISIONED": "Provisioned",
            "DECLINED": "Declined",
            "SUSPENDED": "Suspended",
        }.get(state, state.title() or "Active")

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.open_course.emit(self.course_id)
        super().mouseReleaseEvent(event)
