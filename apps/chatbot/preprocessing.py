import re

from core.rag.text_preprocessing import normalize_user_query

_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")
_PHONE_RE = re.compile(r"(?<!\w)(?:\+?\d[\d\-\s\(\)]{7,}\d)(?!\w)")


def preprocess_user_text(text: str, *, max_length: int | None = None) -> str:
    """
    Normalize user-facing query text without changing meaning:
    - remove control / zero-width chars
    - collapse whitespace
    - trim
    - optionally cap length
    """
    return normalize_user_query(text, max_length=max_length)


def mask_sensitive_data(text: str) -> str:
    """
    Redact common PII patterns before storing logs.
    Keeps line breaks and punctuation as-is to preserve readability.
    """
    value = normalize_user_query(text)
    value = _EMAIL_RE.sub("[REDACTED_EMAIL]", value)
    value = _PHONE_RE.sub("[REDACTED_PHONE]", value)
    return value.strip()
