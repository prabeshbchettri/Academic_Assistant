from __future__ import annotations

import logging
from collections.abc import Iterable
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


def download_drive_file(drive_file_id: str, destination_path: str, scopes: Iterable[str] | None = None) -> bool:
    """
    Downloads a Google Drive attachment file by ID.
    """
    import io
    from googleapiclient.http import MediaIoBaseDownload
    from pathlib import Path

    try:
        credentials = get_credentials(scopes or STUDENT_SCOPES)
        drive_service = build("drive", "v3", credentials=credentials, cache_discovery=False)
        request = drive_service.files().get_media(fileId=drive_file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()

        dest = Path(destination_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(fh.getvalue())
        logger.info("Successfully downloaded Drive file %s to %s", drive_file_id, destination_path)
        return True
    except Exception as exc:
        logger.warning("Failed to download Drive attachment %s: %s", drive_file_id, exc)
        return False




