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



