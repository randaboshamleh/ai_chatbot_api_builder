import re

# Remove non-printable and invisible chars that frequently appear in copied text.
_CONTROL_CHARS_RE = re.compile(r"[\u0000-\u001F\u007F-\u009F]")
_ZERO_WIDTH_RE = re.compile(r"[\u200B-\u200F\uFEFF]")
_WHITESPACE_RE = re.compile(r"\s+")

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
    normalized = text or ""
    normalized = _ZERO_WIDTH_RE.sub("", normalized)
    normalized = _CONTROL_CHARS_RE.sub(" ", normalized)
    normalized = _WHITESPACE_RE.sub(" ", normalized).strip()

    if max_length and max_length > 0:
        normalized = normalized[:max_length].strip()

    return normalized


def mask_sensitive_data(text: str) -> str:
    """
    Redact common PII patterns before storing logs.
    Keeps line breaks and punctuation as-is to preserve readability.
    """
    value = text or ""
    value = _ZERO_WIDTH_RE.sub("", value)
    value = _CONTROL_CHARS_RE.sub(" ", value)
    value = _EMAIL_RE.sub("[REDACTED_EMAIL]", value)
    value = _PHONE_RE.sub("[REDACTED_PHONE]", value)
    return value.strip()
