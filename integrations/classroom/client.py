from __future__ import annotations

import logging
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from googleapiclient.discovery import build

from integrations.google_auth import STUDENT_SCOPES, get_credentials

logger = logging.getLogger(__name__)


def build_classroom_service(scopes: Iterable[str] | None = None) -> Any:
    credentials = get_credentials(scopes or STUDENT_SCOPES)
    return build("classroom", "v1", credentials=credentials, cache_discovery=False)


def list_courses(service: Any) -> list[dict[str, Any]]:
    courses: list[dict[str, Any]] = []
    page_token: str | None = None

    while True:
        response = (
            service.courses()
            .list(pageSize=100, pageToken=page_token)
            .execute()
        )
        courses.extend(response.get("courses", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return courses


def list_coursework(service: Any, course_id: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    page_token: str | None = None

    while True:
        response = (
            service.courses()
            .courseWork()
            .list(courseId=course_id, pageSize=100, pageToken=page_token)
            .execute()
        )
        items.extend(response.get("courseWork", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return items


def list_coursework_materials(service: Any, course_id: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    page_token: str | None = None

    while True:
        response = (
            service.courses()
            .courseWorkMaterials()
            .list(courseId=course_id, pageSize=100, pageToken=page_token)
            .execute()
        )
        items.extend(response.get("courseWorkMaterial", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return items


def extract_materials_summary(item: dict[str, Any]) -> str:
    """Formats attached Classroom materials (Drive files, links, videos) into readable context."""
    materials = item.get("materials") or []
    if not materials:
        return ""

    lines: list[str] = ["Attached Classroom Materials:"]
    for mat in materials:
        if not isinstance(mat, dict):
            continue
        if "driveFile" in mat:
            df = (mat.get("driveFile") or {}).get("driveFile") or {}
            title = df.get("title") or "Drive Attachment"
            link = df.get("alternateLink") or ""
            lines.append(f"- [Drive File] {title}" + (f" ({link})" if link else ""))
        elif "link" in mat:
            lnk = mat.get("link") or {}
            title = lnk.get("title") or lnk.get("url") or "External Link"
            url = lnk.get("url") or ""
            lines.append(f"- [Link] {title}: {url}")
        elif "youtubeVideo" in mat:
            yt = mat.get("youtubeVideo") or {}
            lines.append(f"- [Video] {yt.get('title', 'YouTube')} ({yt.get('alternateLink', '')})")
        elif "form" in mat:
            form = mat.get("form") or {}
            lines.append(f"- [Form] {form.get('title', 'Google Form')} ({form.get('formUrl', '')})")

    return "\n".join(lines) if len(lines) > 1 else ""


def download_drive_file(
    drive_file_id: str,
    destination_path: str,
    scopes: Iterable[str] | None = None,
) -> bool:
    """Downloads a Google Drive attachment file by ID when Drive scope is authorized."""
    import io

    from googleapiclient.http import MediaIoBaseDownload

    try:
        credentials = get_credentials(scopes or STUDENT_SCOPES)
        drive_service = build("drive", "v3", credentials=credentials, cache_discovery=False)
        request = drive_service.files().get_media(fileId=drive_file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _status, done = downloader.next_chunk()

        dest = Path(destination_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(fh.getvalue())
        logger.info("Successfully downloaded Drive file %s to %s", drive_file_id, destination_path)
        return True
    except Exception as exc:
        logger.warning("Failed to download Drive attachment %s: %s", drive_file_id, exc)
        return False
