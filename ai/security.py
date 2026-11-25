from __future__ import annotations

import re
import secrets

MAX_INPUT_CHARS = 100_000

_INJECTION_PATTERNS = (
    r"ignore\s+(?:all\s+|any\s+|previous\s+|the\s+above\s+)*instructions",
    r"disregard\s+(?:all\s+|previous\s+|your\s+)*(?:system\s+)?instructions",
    r"system\s+prompt\s+override",
    r"reveal\s+(?:your\s+)?(?:hidden\s+|internal\s+)?system\s+prompt",
    r"you\s+are\s+now\s+(?:in\s+)?(?:developer|jailbreak|unrestricted)\s+mode",
    r"<\|(?:system|im_start|im_end)\|>",
)
_INJECTION_REGEX = re.compile("|".join(_INJECTION_PATTERNS), re.IGNORECASE)


def sanitize_external_input(text: str) -> str:
    """Caps input length and redacts prompt injection override patterns."""
    if len(text) > MAX_INPUT_CHARS:
        text = text[:MAX_INPUT_CHARS]
    return _INJECTION_REGEX.sub("[REDACTED_SUSPICIOUS_PROMPT]", text)


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
