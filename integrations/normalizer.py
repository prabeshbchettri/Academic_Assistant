from __future__ import annotations

import hashlib
import re
import unicodedata
from pathlib import Path

from integrations.file_parser import parse_file
from models.assignment import NormalizedInput, RawInput


def sanitize_text(text: str) -> str:
    # Normalize unicode to NFC
    text = unicodedata.normalize("NFC", text)
    # Remove control characters except standard whitespace \n \r \t
    text = "".join(ch for ch in text if ch in ("\n", "\r", "\t") or unicodedata.category(ch)[0] != "C")
    # Normalize line breaks
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Collapse 3+ consecutive newlines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def compute_content_hash(text: str, course: str | None = None) -> str:
    hasher = hashlib.sha256()
    if course:
        hasher.update(course.strip().lower().encode("utf-8"))
    # Normalize whitespace before hashing for robust deduplication
    normalized_for_hash = re.sub(r"\s+", " ", text.strip().lower())
    hasher.update(normalized_for_hash.encode("utf-8"))
    return hasher.hexdigest()


def extract_title(text: str, fallback: str = "Academic Assignment") -> str:
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    if not lines:
        return fallback

    # Check for title patterns like "Title: ...", "Assignment: ...", "Lab Report: ..."
    for line in lines[:5]:
        match = re.match(r"^(?:Title|Assignment|Lab|Experiment)\s*[:\-]\s*(.+)$", line, re.IGNORECASE)
        if match:
            return match.group(1).strip()

    # Use first non-empty line up to 80 chars
    first_line = lines[0]
    if len(first_line) > 80:
        return first_line[:77] + "..."
    return first_line


def normalize_input(raw: RawInput) -> NormalizedInput:
    collected_text = raw.raw_text.strip()
    attachments = []

    if raw.file_path:
        path = Path(raw.file_path)
        parsed = parse_file(path)
        attachments.append(str(path))
        if collected_text:
            collected_text = f"{collected_text}\n\n[Attachment: {path.name}]\n{parsed.text}"
        else:
            collected_text = parsed.text

    cleaned = sanitize_text(collected_text)
    title = raw.title.strip() if raw.title else extract_title(cleaned)
    content_hash = compute_content_hash(cleaned, raw.course_name)

    return NormalizedInput(
        title=title,
        cleaned_text=cleaned,
        source_type=raw.source_type,
        content_hash=content_hash,
        course_name=raw.course_name,
        due_date=raw.due_date,
        attachments=attachments,
        metadata=raw.metadata,
    )
