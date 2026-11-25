from __future__ import annotations

import contextlib
import logging
from pathlib import Path

from PySide6.QtCore import QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from sqlmodel import select

from database.db import get_session
from database.models import GeneratedDocumentTable
from database.repositories import AssignmentRepository, DocumentRepository

logger = logging.getLogger(__name__)


class HistoryPage(QWidget):
    edit_requested = Signal(int)

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
        self.table.setHorizontalHeaderLabels(
            ["ID", "Title", "Version", "Engine", "Created At", "Actions"]
        )
        self.table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
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

        self.edit_btn = QPushButton("Edit")
        self.edit_btn.setObjectName("PrimaryButton")
        self.edit_btn.clicked.connect(self._request_edit)
        btn_bar.addWidget(self.edit_btn)

        self.delete_btn = QPushButton("Delete")
        self.delete_btn.setObjectName("DangerButton")
        self.delete_btn.clicked.connect(self._delete_selected)
        btn_bar.addWidget(self.delete_btn)

        btn_bar.addStretch()
        layout.addLayout(btn_bar)

        self.documents_list: list[GeneratedDocumentTable] = []

    def refresh(self) -> None:
        try:
            with get_session() as session:
                assign_repo = AssignmentRepository(session)
                assignments = {a.id: a for a in assign_repo.list_all(limit=100)}

                statement = select(GeneratedDocumentTable).order_by(
                    GeneratedDocumentTable.created_at.desc()  # type: ignore[attr-defined]
                )
                docs = list(session.exec(statement).all())
                self.documents_list = docs

            self.table.setRowCount(len(docs))
            for row, d in enumerate(docs):
                self.table.setItem(row, 0, QTableWidgetItem(str(d.assignment_id)))
                title = (
                    assignments[d.assignment_id].title
                    if d.assignment_id in assignments
                    else "Assignment"
                )
                self.table.setItem(row, 1, QTableWidgetItem(title))
                self.table.setItem(row, 2, QTableWidgetItem(f"v{d.version}"))
                self.table.setItem(row, 3, QTableWidgetItem(d.engine))
                date_str = d.created_at.strftime("%Y-%m-%d %H:%M") if d.created_at else ""
                self.table.setItem(row, 4, QTableWidgetItem(date_str))
                self.table.setItem(row, 5, QTableWidgetItem("DOCX / PDF ready"))
        except Exception as exc:
            logger.warning("Could not refresh document history: %s", exc)

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

    def _request_edit(self) -> None:
        doc = self._get_current_doc()
        if doc is None:
            QMessageBox.warning(
                self,
                "Select a document",
                "Choose a document from the history table first.",
            )
            return
        self.edit_requested.emit(doc.assignment_id)

    def _delete_selected(self) -> None:
        doc = self._get_current_doc()
        if doc is None:
            QMessageBox.warning(
                self,
                "Select a document",
                "Choose a document from the history table first.",
            )
            return

        reply = QMessageBox.question(
            self,
            "Delete document",
            "Delete this document and all of its versions?\n\n"
            "The generated files will also be removed from disk.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        assignment_id = doc.assignment_id
        file_pairs: list[tuple[str, str | None]] = []
        with get_session() as session:
            docs = DocumentRepository(session).list_by_assignment(assignment_id)
            file_pairs = [(d.docx_path, d.pdf_path) for d in docs]
            AssignmentRepository(session).delete(assignment_id)

        for docx_path, pdf_path in file_pairs:
            self._remove_document_files(docx_path, pdf_path)
        self.refresh()

    @staticmethod
    def _remove_document_files(docx_path: str, pdf_path: str | None) -> None:
        parents: set[Path] = set()
        for raw_path in (docx_path, pdf_path):
            if not raw_path:
                continue
            path = Path(raw_path)
            parents.add(path.parent)
            if path.exists():
                path.unlink()

        for parent in parents:
            for extra in ("report.tex", "metadata.json"):
                extra_path = parent / extra
                if extra_path.exists():
                    extra_path.unlink()
            with contextlib.suppress(OSError):
                parent.rmdir()
