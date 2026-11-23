from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from app.ui.widgets.progress_log import ProgressLogWidget


class ProcessingPage(QWidget):
    cancel_requested = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        header = QLabel("Academic Document Workflow Execution")
        header.setStyleSheet("font-size: 20px; font-weight: bold; color: #1B365D;")
        layout.addWidget(header)

        self.progress_log = ProgressLogWidget()
        layout.addWidget(self.progress_log)

    def reset(self) -> None:
        self.progress_log.reset()

    def update_node_step(self, node_name: str, message: str) -> None:
        self.progress_log.update_node(node_name, message)
