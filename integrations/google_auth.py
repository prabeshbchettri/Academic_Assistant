from __future__ import annotations

import json
import logging
import os
from collections.abc import Iterable, Sequence

# Allow oauthlib to accept Google's returned scopes without crashing on harmless differences.
os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"

import keyring
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from app.settings import settings

logger = logging.getLogger(__name__)

KEYRING_SERVICE = "academic-ai"
KEYRING_USERNAME = "google-oauth"
TOKEN_PATH = settings.storage_dir / "credentials" / "google_token.json"

STUDENT_SCOPES: tuple[str, ...] = (
    "https://www.googleapis.com/auth/classroom.courses.readonly",
    "https://www.googleapis.com/auth/classroom.coursework.me.readonly",
    "https://www.googleapis.com/auth/classroom.courseworkmaterials.readonly",
    "https://www.googleapis.com/auth/classroom.student-submissions.me.readonly",
)


class GoogleAuthError(RuntimeError):
    """Raised when Google OAuth cannot be completed."""


def _read_token() -> Credentials | None:
    try:
        payload = keyring.get_password(KEYRING_SERVICE, KEYRING_USERNAME)
        if payload:
            creds = Credentials.from_authorized_user_info(json.loads(payload))
            # Mirror to persistent file if missing
            if not TOKEN_PATH.exists():
                TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
                TOKEN_PATH.write_text(payload, encoding="utf-8")
                TOKEN_PATH.chmod(0o600)
            return creds
    except Exception as exc:
        logger.warning("Could not read token from keyring: %s", exc)

    if TOKEN_PATH.exists():
        try:
            return Credentials.from_authorized_user_file(str(TOKEN_PATH))
        except Exception as exc:
            logger.warning("Could not read token file: %s", exc)

    return None


def _write_token(credentials: Credentials) -> None:
    payload = credentials.to_json()
    # Save to OS keyring
    try:
        keyring.set_password(KEYRING_SERVICE, KEYRING_USERNAME, payload)
        logger.info("Stored Google token in the OS keyring.")
    except Exception as exc:
        logger.warning("Could not write token to keyring: %s", exc)

    # Also always save to persistent file backup (mode 600)
    try:
        TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_PATH.write_text(payload, encoding="utf-8")
        TOKEN_PATH.chmod(0o600)
        logger.info("Stored Google token at %s", TOKEN_PATH)
    except Exception as exc:
        logger.warning("Could not write token to file: %s", exc)


def _has_scopes(credentials: Credentials, scopes: Sequence[str]) -> bool:
    if not credentials.scopes:
        return True
    granted = set(credentials.scopes)
    requested = set(scopes)

    # Google often returns student-submissions.me.readonly instead of coursework.me.readonly
    equiv_cw = "https://www.googleapis.com/auth/classroom.coursework.me.readonly"
    equiv_sub = "https://www.googleapis.com/auth/classroom.student-submissions.me.readonly"
    if equiv_cw in requested and equiv_sub in granted:
        requested.remove(equiv_cw)
        requested.add(equiv_sub)

    return requested.issubset(granted)


def is_authenticated() -> bool:
    creds = _read_token()
    return creds is not None and (creds.valid or bool(creds.refresh_token))


def get_credentials(scopes: Iterable[str] = STUDENT_SCOPES) -> Credentials:
    requested = tuple(scopes)
    credentials = _read_token()

    if credentials and _has_scopes(credentials, requested):
        if credentials.valid:
            return credentials
        if credentials.expired and credentials.refresh_token:
            try:
                credentials.refresh(Request())
                _write_token(credentials)
                return credentials
            except Exception as exc:
                logger.warning("Token refresh failed: %s", exc)

    client_file = settings.google_oauth_client_path
    if not client_file.exists():
        raise GoogleAuthError(
            f"OAuth client file not found: {client_file}. "
            "Download the desktop client JSON and save it there."
        )

    logger.info("Starting Google OAuth flow with scopes: %s", ", ".join(requested))
    flow = InstalledAppFlow.from_client_secrets_file(str(client_file), list(requested))
    credentials = flow.run_local_server(port=0, open_browser=True, prompt="consent")
    _write_token(credentials)
    return credentials
