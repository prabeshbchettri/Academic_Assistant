from app.settings import PROJECT_ROOT, Settings


def test_defaults_do_not_require_env() -> None:
    settings = Settings(_env_file=None)
    assert settings.app_name == "Academic AI"
    assert settings.gemini_model == "gemini-2.5-flash-lite"
    assert settings.llm_provider == "nvidia"
    assert settings.nvidia_model == "nvidia/nemotron-3-ultra-550b-a55b"
    assert settings.nvidia_base_url == "https://integrate.api.nvidia.com/v1"
    assert settings.pdf_engine == "tectonic"
    assert settings.gemini_api_key.get_secret_value() == ""
    assert settings.nvidia_api_key.get_secret_value() == ""


def test_google_client_path_resolves_against_project_root() -> None:
    settings = Settings(_env_file=None)
    assert settings.google_oauth_client_path == PROJECT_ROOT / "credentials.json"


def test_storage_paths() -> None:
    settings = Settings(_env_file=None)
    assert settings.logs_dir == settings.storage_dir / "logs"
