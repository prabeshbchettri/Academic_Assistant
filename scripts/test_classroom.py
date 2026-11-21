from __future__ import annotations

import argparse
import json
import logging
import sys
from typing import Any

from googleapiclient.errors import HttpError

from integrations.classroom.client import (
    build_classroom_service,
    list_courses,
    list_coursework,
    list_coursework_materials,
)

logger = logging.getLogger(__name__)


def _print_course(course: dict[str, Any]) -> None:
    print(f"- {course.get('name', '(unnamed)')}")
    print(f"  id: {course.get('id')}")
    print(f"  section: {course.get('section', '-')}")
    print(f"  state: {course.get('courseState', '-')}")
    print(f"  link: {course.get('alternateLink', '-')}")


def _print_work(item: dict[str, Any]) -> None:
    print(f"- {item.get('title', '(untitled)')}")
    print(f"  id: {item.get('id')}")
    print(f"  type: {item.get('workType', '-')}")
    print(f"  state: {item.get('state', '-')}")
    print(f"  maxPoints: {item.get('maxPoints', '-')}")
    due = item.get("dueDate")
    if due:
        month = due.get("month", 0)
        day = due.get("day", 0)
        print(f"  due: {due.get('year')}-{month:02d}-{day:02d}")
    print(f"  materials: {len(item.get('materials', []))}")
    print(f"  link: {item.get('alternateLink', '-')}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Test student Google Classroom access.")
    parser.add_argument(
        "--course-id",
        help="Course ID to inspect. Defaults to the first course.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the raw courses response as JSON.",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    try:
        service = build_classroom_service()
        courses = list_courses(service)
    except HttpError as exc:
        print(f"Google Classroom API error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Authentication/setup error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(courses, indent=2))
        return 0

    if not courses:
        print("No courses found.")
        print("Check that the signed-in account is enrolled and has accepted the")
        print("Classroom invitation.")
        return 0

    print(f"Found {len(courses)} course(s):")
    for course in courses:
        _print_course(course)

    course_id = args.course_id or courses[0]["id"]
    print(f"\nCoursework for course {course_id}:")
    try:
        work = list_coursework(service, course_id)
        materials = list_coursework_materials(service, course_id)
    except HttpError as exc:
        print(f"Could not list coursework: {exc}", file=sys.stderr)
        return 1

    if not work:
        print("No coursework found.")
    for item in work:
        _print_work(item)

    print(f"\nCoursework materials: {len(materials)}")
    for item in materials:
        print(
            f"- {item.get('title', '(untitled)')} "
            f"(id={item.get('id')}, state={item.get('state', '-')})"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
