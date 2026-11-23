from __future__ import annotations

import re
import secrets

MAX_INPUT_CHARS = 100_000


def sanitize_external_input(text: str) -> str:
    """Caps input length and strips dangerous control characters."""
    if len(text) > MAX_INPUT_CHARS:
        text = text[:MAX_INPUT_CHARS]
    # Redact common prompt injection patterns
    redacted = re.sub(
        r"(?i)(ignore\s+all\s+previous\s+instructions|system\s+prompt\s+override|reveal\s+your\s+system\s+prompt)",
        "[REDACTED_SUSPICIOUS_PROMPT]",
        text,
    )
    return redacted


def wrap_untrusted_data(text: str) -> tuple[str, str]:
    """
    Wraps untrusted data inside a uniquely generated delimiter token so
    the LLM cannot confuse user content with system instructions.
    """
    boundary_token = secrets.token_hex(8)
    wrapped = (
        f"--- START UNTRUSTED EXTERNAL DATA [{boundary_token}] ---\n"
        f"{sanitize_external_input(text)}\n"
        f"--- END UNTRUSTED EXTERNAL DATA [{boundary_token}] ---"
    )
    return wrapped, boundary_token
