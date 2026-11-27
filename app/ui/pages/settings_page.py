from __future__ import annotations

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

from app.settings import PROJECT_ROOT, settings
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

        # NVIDIA NIM API Key
        c_layout.addWidget(QLabel("NVIDIA NIM API Key:"))
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.Password)
        key_val = (
            settings.nvidia_api_key.get_secret_value()
            if hasattr(settings.nvidia_api_key, "get_secret_value")
            else str(settings.nvidia_api_key or "")
        )
        self.api_key_input.setText(key_val)
        c_layout.addWidget(self.api_key_input)

        # NVIDIA Model
        c_layout.addWidget(QLabel("Primary NVIDIA Model:"))
        self.model_combo = QComboBox()
        models = [
            "nvidia/nemotron-3.5-lightning-30b-a3b",
            "nvidia/nemotron-3.5-bolt-e4b",
            "mistralai/mistral-large-4-1t-a52b",
        ]
        if settings.nvidia_model not in models:
            models.insert(0, settings.nvidia_model)
        self.model_combo.addItems(models)
        self.model_combo.setCurrentText(settings.nvidia_model)
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
        self.google_status_label = QLabel(
            "Status: Connected" if is_authenticated() else "Status: Not Connected"
        )
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

    def reload_preferences(self) -> None:
        """Refresh editable values from persisted preferences."""
        return

    def _test_google_oauth(self) -> None:
        try:
            from integrations.google_auth import get_credentials
            creds = get_credentials()
            if creds and creds.valid:
                self.google_status_label.setText("Status: Successfully Connected!")
                QMessageBox.information(
                    self,
                    "Google OAuth",
                    "Google account authorized successfully.",
                )
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Google OAuth Error",
                f"OAuth flow could not complete: {exc}",
            )

    def _save_settings(self) -> None:
        new_key = self.api_key_input.text().strip()
        new_model = self.model_combo.currentText()
        new_pdf = self.pdf_engine_combo.currentText()

        # Update runtime settings
        from pydantic import SecretStr
        settings.nvidia_api_key = SecretStr(new_key)
        settings.nvidia_model = new_model
        settings.pdf_engine = new_pdf

        # Write to the project-root .env that app.settings loads.
        env_file = PROJECT_ROOT / ".env"
        lines = (
            env_file.read_text(encoding="utf-8").splitlines()
            if env_file.exists()
            else []
        )
        for key, value in (
            ("NVIDIA_API_KEY", new_key),
            ("NVIDIA_MODEL", new_model),
            ("PDF_ENGINE", new_pdf),
        ):
            lines = self._upsert_env_line(lines, key, value)
        env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        QMessageBox.information(self, "Settings", "Settings saved successfully.")

    @staticmethod
    def _upsert_env_line(lines: list[str], key: str, value: str) -> list[str]:
        prefix = f"{key}="
        for index, line in enumerate(lines):
            if line.startswith(prefix):
                lines[index] = f"{key}={value}"
                return lines
        lines.append(f"{key}={value}")
        return lines
