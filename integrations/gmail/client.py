from __future__ import annotations

import base64
import logging
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from googleapiclient.discovery import build

from app.settings import settings
from integrations.google_auth import STUDENT_SCOPES, get_credentials

logger = logging.getLogger(__name__)


def build_gmail_service(scopes: Iterable[str] | None = None) -> Any:
    credentials = get_credentials(scopes or STUDENT_SCOPES)
    return build("gmail", "v1", credentials=credentials, cache_discovery=False)


def search_messages(service: Any, query: str = "assignment OR syllabus OR lab", max_results: int = 20) -> list[dict[str, Any]]:
    results = service.users().messages().list(userId="me", q=query, maxResults=max_results).execute()
    messages = results.get("messages", [])

    detailed_messages = []
    for msg in messages:
        msg_id = msg["id"]
        detail = service.users().messages().get(userId="me", id=msg_id, format="full").execute()
        headers = {h["name"].lower(): h["value"] for h in detail.get("payload", {}).get("headers", [])}
        subject = headers.get("subject", "No Subject")
        sender = headers.get("from", "Unknown")
        date = headers.get("date", "")
        snippet = detail.get("snippet", "")

        detailed_messages.append({
            "id": msg_id,
            "subject": subject,
            "sender": sender,
            "date": date,
            "snippet": snippet,
        })

    return detailed_messages


def get_message_content_and_attachments(service: Any, message_id: str, download_dir: Path | None = None) -> dict[str, Any]:
    detail = service.users().messages().get(userId="me", id=message_id, format="full").execute()
    payload = detail.get("payload", {})

    body_text = ""
    attachments = []
    target_dir = download_dir or (settings.storage_dir / "inputs" / "gmail")
    target_dir.mkdir(parents=True, exist_ok=True)

    def extract_parts(parts):
        nonlocal body_text
        for part in parts:
            mime = part.get("mimeType", "")
            data = part.get("body", {}).get("data")
            if mime == "text/plain" and data:
                try:
                    body_text += base64.urlsafe_b64decode(data).decode("utf-8")
                except Exception:
                    pass

            filename = part.get("filename")
            att_id = part.get("body", {}).get("attachmentId")
            if filename and att_id:
                try:
                    att = service.users().messages().attachments().get(
                        userId="me", messageId=message_id, id=att_id
                    ).execute()
                    file_data = base64.urlsafe_b64decode(att.get("data", ""))
                    save_path = target_dir / filename
                    save_path.write_bytes(file_data)
                    attachments.append(str(save_path))
                except Exception as exc:
                    logger.warning("Could not download attachment %s: %s", filename, exc)

            if "parts" in part:
                extract_parts(part["parts"])

    if "parts" in payload:
        extract_parts(payload["parts"])
    elif payload.get("body", {}).get("data"):
        try:
            body_text = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")
        except Exception:
            pass

    return {
        "id": message_id,
        "body_text": body_text or detail.get("snippet", ""),
        "attachments": attachments,
    }
