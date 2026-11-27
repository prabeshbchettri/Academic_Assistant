from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "Academic AI"
    log_level: str = "INFO"

    nvidia_api_key: SecretStr = SecretStr("")
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    nvidia_model: str = "nvidia/nemotron-3.5-lightning-30b-a3b"
    nvidia_fallback_model: str = "nvidia/nemotron-3.5-bolt-e4b"
    nvidia_max_output_tokens: int = 8192
    nvidia_timeout_seconds: int = 60
    nvidia_enable_thinking: bool = False
    nvidia_embedding_model: str = "nvidia/nemotron-3.5-embed-1b"
    nvidia_embedding_dimensions: int = 1024

    google_oauth_client_file: Path = Path("credentials.json")
    google_token_store: str = "keyring"

    pdf_engine: str = "tectonic"
    pdf_fallback_engine: str = "libreoffice"
    tectonic_path: str = ""

    storage_dir: Path = PROJECT_ROOT / "storage"

    @property
    def logs_dir(self) -> Path:
        return self.storage_dir / "logs"

    @property
    def google_oauth_client_path(self) -> Path:
        path = self.google_oauth_client_file
        return path if path.is_absolute() else PROJECT_ROOT / path

    def require_nvidia_key(self) -> str:
        value = self.nvidia_api_key_str
        if not value:
            raise RuntimeError("NVIDIA_API_KEY is not set. Add it to .env.")
        return value

    @property
    def nvidia_api_key_str(self) -> str:
        if hasattr(self.nvidia_api_key, "get_secret_value"):
            return self.nvidia_api_key.get_secret_value().strip()
        return str(self.nvidia_api_key or "").strip()


settings = Settings()
