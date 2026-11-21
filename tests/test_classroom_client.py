from __future__ import annotations

from typing import Any

from integrations.classroom.client import list_courses


class _Request:
    def __init__(self, response: dict[str, Any]) -> None:
        self._response = response

    def execute(self) -> dict[str, Any]:
        return self._response


class _CoursesResource:
    def __init__(self, pages: list[dict[str, Any]]) -> None:
        self._pages = pages
        self._index = 0

    def list(self, **_: Any) -> _Request:
        page = self._pages[self._index]
        self._index += 1
        return _Request(page)


class _Service:
    def __init__(self, pages: list[dict[str, Any]]) -> None:
        self._courses = _CoursesResource(pages)

    def courses(self) -> _CoursesResource:
        return self._courses


def test_list_courses_paginates() -> None:
    service = _Service(
        [
            {"courses": [{"id": "1"}], "nextPageToken": "next"},
            {"courses": [{"id": "2"}]},
        ]
    )

    assert [course["id"] for course in list_courses(service)] == ["1", "2"]
