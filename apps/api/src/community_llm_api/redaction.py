from __future__ import annotations

import re

_TOKEN_PATTERN = re.compile(r"\b(?:clm_|wrk_)[A-Za-z0-9_-]+")
_BEARER_PATTERN = re.compile(r"(Bearer\s+)[A-Za-z0-9._~+/=-]+", re.IGNORECASE)
_AUTH_HEADER_PATTERN = re.compile(r"(Authorization:\s*)\S+", re.IGNORECASE)
_SECRET_ASSIGNMENT_PATTERN = re.compile(r"(?i)\b(password|secret|token|api[_-]?key)\s*[=:]\s*\S+")


def redact_logs(text: str | None, limit: int = 20000) -> str | None:
    if not text:
        return None
    redacted = text[:limit]
    redacted = _TOKEN_PATTERN.sub("[redacted-token]", redacted)
    redacted = _BEARER_PATTERN.sub(r"\1[redacted]", redacted)
    redacted = _AUTH_HEADER_PATTERN.sub(r"\1[redacted]", redacted)
    redacted = _SECRET_ASSIGNMENT_PATTERN.sub(r"\1=[redacted]", redacted)
    return redacted
