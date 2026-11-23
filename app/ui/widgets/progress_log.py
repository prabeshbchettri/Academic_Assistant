from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class ProgressLogWidget(QWidget):
    NODES_SEQUENCE = [
        "normalize",
        "classify",
        "load_config",
        "check_missing_info",
        "retrieve_references",
        "generate_content",
        "evaluate_output",
        "human_review",
        "export",
        "persist",
    ]

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        header = QHBoxLayout()
        self.status_label = QLabel("Initializing workflow...")
        self.status_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #1B365D;")
        header.addWidget(self.status_label)
        header.addStretch()

        self.retry_label = QLabel("")
        self.retry_label.setStyleSheet("color: #D97706; font-weight: 600;")
        header.addWidget(self.retry_label)
        layout.addLayout(header)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, len(self.NODES_SEQUENCE))
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setStyleSheet("background-color: #1E293B; color: #F8FAFC; font-family: monospace; font-size: 12px;")
        layout.addWidget(self.log_box)

    def reset(self) -> None:
        self.progress_bar.setValue(0)
        self.status_label.setText("Starting workflow...")
        self.retry_label.setText("")
        self.log_box.clear()

    def update_node(self, node_name: str, message: str) -> None:
        clean_node = node_name.replace("regenerate_failed_attempt_", "retry_")
        if clean_node in self.NODES_SEQUENCE:
            idx = self.NODES_SEQUENCE.index(clean_node) + 1
            self.progress_bar.setValue(idx)

        self.status_label.setText(f"Active Step: {node_name.replace('_', ' ').title()}")
        self.log_box.append(f"[{node_name}] {message}")

        if "retry" in node_name:
            self.retry_label.setText(f"Regenerating Section ({node_name})")
