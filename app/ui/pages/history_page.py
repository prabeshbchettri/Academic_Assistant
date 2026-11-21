from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
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


class HistoryPage(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        header = QLabel("Exported Academic Documents History")
        header.setStyleSheet("font-size: 20px; font-weight: bold; color: #1B365D;")
        layout.addWidget(header)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["ID", "Title", "Version", "Engine", "Created At", "Actions"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        layout.addWidget(self.table)

        btn_bar = QHBoxLayout()
        self.open_docx_btn = QPushButton("Open DOCX")
        self.open_docx_btn.setObjectName("SecondaryButton")
        self.open_docx_btn.clicked.connect(self._open_selected_docx)
        btn_bar.addWidget(self.open_docx_btn)

        self.open_pdf_btn = QPushButton("Open PDF")
        self.open_pdf_btn.setObjectName("SecondaryButton")
        self.open_pdf_btn.clicked.connect(self._open_selected_pdf)
        btn_bar.addWidget(self.open_pdf_btn)

        self.open_folder_btn = QPushButton("Open Output Folder")
        self.open_folder_btn.setObjectName("SecondaryButton")
        self.open_folder_btn.clicked.connect(self._open_selected_folder)
        btn_bar.addWidget(self.open_folder_btn)

        btn_bar.addStretch()
        layout.addLayout(btn_bar)

        self.documents_list = []

    def refresh(self) -> None:
        try:
            with get_session() as session:
                assign_repo = AssignmentRepository(session)
                assignments = {a.id: a for a in assign_repo.list_all(limit=100)}

                from sqlmodel import select

                from database.models import GeneratedDocumentTable
                statement = select(GeneratedDocumentTable).order_by(GeneratedDocumentTable.created_at.desc())  # type: ignore
                docs = list(session.exec(statement).all())
                self.documents_list = docs

            self.table.setRowCount(len(docs))
            for row, d in enumerate(docs):
                self.table.setItem(row, 0, QTableWidgetItem(str(d.assignment_id)))
                title = assignments[d.assignment_id].title if d.assignment_id in assignments else "Assignment"
                self.table.setItem(row, 1, QTableWidgetItem(title))
                self.table.setItem(row, 2, QTableWidgetItem(f"v{d.version}"))
                self.table.setItem(row, 3, QTableWidgetItem(d.engine))
                date_str = d.created_at.strftime("%Y-%m-%d %H:%M") if d.created_at else ""
                self.table.setItem(row, 4, QTableWidgetItem(date_str))
                self.table.setItem(row, 5, QTableWidgetItem("DOCX / PDF ready"))
        except Exception:
            pass

    def _get_current_doc(self):
        row = self.table.currentRow()
        if 0 <= row < len(self.documents_list):
            return self.documents_list[row]
        return None

    def _open_selected_docx(self) -> None:
        doc = self._get_current_doc()
        if doc and doc.docx_path and Path(doc.docx_path).exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(doc.docx_path))

    def _open_selected_pdf(self) -> None:
        doc = self._get_current_doc()
        if doc and doc.pdf_path and Path(doc.pdf_path).exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(doc.pdf_path))

    def _open_selected_folder(self) -> None:
        doc = self._get_current_doc()
        if doc and doc.docx_path:
            folder = str(Path(doc.docx_path).parent)
            QDesktopServices.openUrl(QUrl.fromLocalFile(folder))
