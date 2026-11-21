from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.settings import settings
from integrations.google_auth import is_authenticated


class SettingsPage(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("Application Settings & Connections")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #1B365D;")
        layout.addWidget(title)

        card = QFrame()
        card.setProperty("class", "Card")
        c_layout = QVBoxLayout(card)
        c_layout.setSpacing(14)

        # Gemini API Key
        c_layout.addWidget(QLabel("Google Gemini API Key:"))
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.Password)
        key_val = (
            settings.gemini_api_key.get_secret_value()
            if hasattr(settings.gemini_api_key, "get_secret_value")
            else str(settings.gemini_api_key or "")
        )
        self.api_key_input.setText(key_val)
        c_layout.addWidget(self.api_key_input)

        # Gemini Model
        c_layout.addWidget(QLabel("Primary Gemini Model:"))
        self.model_combo = QComboBox()
        self.model_combo.addItems([
            "gemini-3.6-flash",
            "gemini-3.5-flash",
            "gemini-3.1-pro-preview",
            "gemini-2.5-flash",
        ])
        self.model_combo.setCurrentText(settings.gemini_model)
        c_layout.addWidget(self.model_combo)

        # PDF Engine
        c_layout.addWidget(QLabel("Default PDF Compilation Engine:"))
        self.pdf_engine_combo = QComboBox()
        self.pdf_engine_combo.addItems(["tectonic", "libreoffice", "system xelatex"])
        self.pdf_engine_combo.setCurrentText(settings.pdf_engine)
        c_layout.addWidget(self.pdf_engine_combo)

        # Google Account Connection Status
        c_layout.addWidget(QLabel("Google Workspace Integration:"))
        google_bar = QHBoxLayout()
        self.google_status_label = QLabel("Status: Connected" if is_authenticated() else "Status: Not Connected")
        self.google_status_label.setStyleSheet("font-weight: 600;")
        google_bar.addWidget(self.google_status_label)

        self.connect_google_btn = QPushButton("Test / Authorize Google OAuth")
        self.connect_google_btn.setObjectName("SecondaryButton")
        self.connect_google_btn.clicked.connect(self._test_google_oauth)
        google_bar.addWidget(self.connect_google_btn)
        google_bar.addStretch()
        c_layout.addLayout(google_bar)

        layout.addWidget(card)

        # Save Button
        save_btn = QPushButton("Save Settings")
        save_btn.setObjectName("PrimaryButton")
        save_btn.clicked.connect(self._save_settings)
        layout.addWidget(save_btn)
        layout.addStretch()

    def _test_google_oauth(self) -> None:
        try:
            from integrations.google_auth import get_credentials
            creds = get_credentials()
            if creds and creds.valid:
                self.google_status_label.setText("Status: Successfully Connected!")
                QMessageBox.information(self, "Google OAuth", "Google account authorized successfully.")
        except Exception as exc:
            QMessageBox.critical(self, "Google OAuth Error", f"OAuth flow could not complete: {exc}")

    def _save_settings(self) -> None:
        new_key = self.api_key_input.text().strip()
        new_model = self.model_combo.currentText()
        new_pdf = self.pdf_engine_combo.currentText()

        # Update runtime settings
        from pydantic import SecretStr
        settings.gemini_api_key = SecretStr(new_key)
        settings.gemini_model = new_model
        settings.pdf_engine = new_pdf

        # Write to .env
        env_file = Path(__file__).resolve().parent.parent.parent / ".env"
        lines = []
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                if line.startswith("GEMINI_API_KEY="):
                    lines.append(f"GEMINI_API_KEY={new_key}")
                elif line.startswith("GEMINI_MODEL="):
                    lines.append(f"GEMINI_MODEL={new_model}")
                elif line.startswith("PDF_ENGINE="):
                    lines.append(f"PDF_ENGINE={new_pdf}")
                else:
                    lines.append(line)
        env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        QMessageBox.information(self, "Settings", "Settings saved successfully.")
