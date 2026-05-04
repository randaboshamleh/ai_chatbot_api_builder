import re
from typing import Iterable

# Control / invisible characters that often appear in copied text or OCR output.
_CONTROL_CHARS_RE = re.compile(r"[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F-\u009F]")
_ZERO_WIDTH_RE = re.compile(r"[\u200B-\u200F\uFEFF\u2066-\u2069]")
_REPLACEMENT_RE = re.compile(r"[\uFFFD]")
_HANGUL_RE = re.compile(r"[\u1100-\u11FF\u3130-\u318F\uAC00-\uD7AF]+")
_CYRILLIC_RE = re.compile(r"[\u0400-\u04FF]+")
_NOISE_SYMBOLS_RE = re.compile(r"[\u25A0-\u25FF\u2600-\u26FF\u2700-\u27BF\uE000-\uF8FF]")

_SPACES_RE = re.compile(r"[ \t\f\v]+")
_MULTI_NL_RE = re.compile(r"\n{3,}")
_MULTI_PUNCT_RE = re.compile(r"([?!\u061F.,:;\u060C\u061B])\1{1,}")
_SPACED_CAPS_WORD_RE = re.compile(r"\b(?:[A-Z]{1,3}\s+){2,}[A-Z]{1,3}\b")
_TRAILING_SPLIT_LETTER_RE = re.compile(r"\b([A-Za-z]{3,})\s+([A-Za-z])\b")
_LEADING_SPLIT_LETTER_RE = re.compile(r"\b([A-Za-z])\s+([A-Za-z]{3,})\b")
_LATIN_CAMEL_BOUNDARY_RE = re.compile(r"([a-z])([A-Z])")
_MERGED_ARTICLE_RE = re.compile(r"\b(for|to|in|on|of|with|from|by|at)(a|an)\b", re.IGNORECASE)

_AR_DIACRITICS_RE = re.compile(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]")

_META_LINE_PATTERNS = [
    re.compile(r"^\s*here is the answer[:\s]*$", re.IGNORECASE),
    re.compile(r"^\s*answer[:\s]*$", re.IGNORECASE),
    re.compile(r"^\s*translation[:\s]*$", re.IGNORECASE),
    re.compile(r"^\s*\(note:.*\)\s*$", re.IGNORECASE),
    re.compile(r"^\s*note:.*$", re.IGNORECASE),
    re.compile(r"^\s*based on the provided context.*$", re.IGNORECASE),
    re.compile(r"^\s*based on the available documents.*$", re.IGNORECASE),
    re.compile(r"^\s*since the question is in arabic.*$", re.IGNORECASE),
    re.compile(r"^\s*without translating.*$", re.IGNORECASE),
    re.compile(r"^\s*if the input is a list.*$", re.IGNORECASE),
    re.compile(r"^\s*if the input is.*multi[-\s]?line.*$", re.IGNORECASE),
    re.compile(r"^\s*keep (?:the )?same list structure.*$", re.IGNORECASE),
    re.compile(r"^\s*do not add facts.*$", re.IGNORECASE),
    re.compile(r"^\s*keep .* technical .* as[-\s]?is.*$", re.IGNORECASE),
    re.compile(r"^\s*keep .*sql.* as[-\s]?is.*$", re.IGNORECASE),
    re.compile(r"^\s*return .*arabic.* text only.*$", re.IGNORECASE),
    re.compile(r"^\s*\*+\s*text\s*:\s*\*+.*$", re.IGNORECASE),
    re.compile(r"^\s*text\s*:\s*$", re.IGNORECASE),
    re.compile(r"^\s*arabic\s*:\s*$", re.IGNORECASE),
    re.compile(r"^\s*(?:ط¥ط°ط§|ط§ط°ط§)\s+ظƒط§ظ†\s+ط§ظ„ط¥ط¯ط®ط§ظ„.*$", re.IGNORECASE),
    re.compile(r"^\s*ظ„ط§\s+طھط¶ظپ\s+ط£ظٹ\s+ط­ظ‚ط§ط¦ظ‚.*$", re.IGNORECASE),
    re.compile(r"^\s*ط§ط­طھظپط¸\s+.*\s+SQL.*$", re.IGNORECASE),
    re.compile(r"^\s*ط£ط±ط¬ط¹\s+.*\s+ط§ظ„ط¹ط±ط¨ظٹ.*$", re.IGNORECASE),
    re.compile(r"^\s*\u0628\u062d\u0633\u0628\s+\u0627\u0644\u0648\u062b\u0627\u0626\u0642\s+\u0627\u0644\u0645\u062a\u0627\u062d\u0629[:\s]*$", re.IGNORECASE),
]
_QUESTION_PREFIX_RE = re.compile(
    r"^(?:what|why|how|when|where|who|which|can|does|is|are)\b|^(?:\u0645\u0627\s+\u0647\u0648|\u0645\u0627\u0630\u0627|\u0644\u0645\u0627\u0630\u0627|\u0643\u064a\u0641|\u0645\u062a\u0649|\u0627\u064a\u0646|\u0645\u0646\s+\u0647\u0648|\u0647\u0644)\b",
    re.IGNORECASE,
)

_ARABIC_MAP = str.maketrans(
    {
        "\u0623": "\u0627",
        "\u0625": "\u0627",
        "\u0622": "\u0627",
        "\u0671": "\u0627",
        "\u0649": "\u064A",
        "\u0624": "\u0648",
        "\u0626": "\u064A",
        "\u0629": "\u0647",
    }
)

_ARABIC_CHARS_RE = re.compile(r"[\u0600-\u06FF]")
_SQL_KEYWORD_RE = re.compile(
    r"\b(?:CREATE|GRANT|ALTER|DROP|INSERT|UPDATE|DELETE|SELECT|TABLESPACE|PROFILE|ROLE|USER)\b",
    re.IGNORECASE,
)
_LIST_LINE_RE = re.compile(r"^\s*(?:[-\u2022]|\d{1,2}[\)\.\-])\s+")


def _clean_common(text: str, *, preserve_newlines: bool) -> str:
    value = text or ""
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    value = _ZERO_WIDTH_RE.sub("", value)
    value = _REPLACEMENT_RE.sub(" ", value)
    value = _CONTROL_CHARS_RE.sub(" ", value)
    value = _NOISE_SYMBOLS_RE.sub(" ", value)

    if preserve_newlines:
        lines: list[str] = []
        for line in value.split("\n"):
            collapsed = _SPACES_RE.sub(" ", line).strip()
            lines.append(collapsed)
        value = "\n".join(lines)
        value = _MULTI_NL_RE.sub("\n\n", value).strip()
    else:
        value = _SPACES_RE.sub(" ", value.replace("\n", " ")).strip()

    value = _MULTI_PUNCT_RE.sub(r"\1", value)
    value = _repair_spaced_latin_words(value)
    return value


def _repair_spaced_latin_words(text: str) -> str:
    def _join_caps(match: re.Match[str]) -> str:
        return re.sub(r"\s+", "", match.group(0))

    value = _SPACED_CAPS_WORD_RE.sub(_join_caps, text)
    # Common OCR split patterns: "TESTIN G" or "K ATALON".
    for _ in range(2):
        value = _TRAILING_SPLIT_LETTER_RE.sub(r"\1\2", value)
        value = _LEADING_SPLIT_LETTER_RE.sub(r"\1\2", value)
    value = _LATIN_CAMEL_BOUNDARY_RE.sub(r"\1 \2", value)
    value = _MERGED_ARTICLE_RE.sub(lambda m: f"{m.group(1)} {m.group(2)}", value)
    return value


def normalize_user_query(text: str, *, max_length: int | None = None) -> str:
    value = _clean_common(text, preserve_newlines=False)
    if max_length and max_length > 0:
        value = value[:max_length].strip()
    return value


def normalize_document_text(text: str) -> str:
    value = _clean_common(text, preserve_newlines=True)

    # Drop repeated short line noise from OCR/page extraction.
    lines = []
    for line in value.split("\n"):
        stripped = line.strip()
        if not stripped:
            lines.append("")
            continue
        if re.fullmatch(r"[-_=~\u2022\u00B7\d\s]{1,8}", stripped):
            continue
        lines.append(stripped)

    value = "\n".join(lines)
    value = _MULTI_NL_RE.sub("\n\n", value).strip()
    return value


def normalize_for_search(text: str) -> str:
    value = normalize_user_query(text).lower()
    value = _AR_DIACRITICS_RE.sub("", value).replace("\u0640", "")
    value = value.translate(_ARABIC_MAP)
    value = re.sub(r"[^\w\u0600-\u06FF\s:+#./-]", " ", value)
    value = _SPACES_RE.sub(" ", value).strip()
    return value


def looks_arabic(text: str) -> bool:
    return bool(_ARABIC_CHARS_RE.search(text or ""))


def remove_meta_scaffolding(text: str) -> str:
    lines = []
    for raw in (text or "").split("\n"):
        line = raw.strip()
        if not line:
            continue
        if any(pattern.match(line) for pattern in _META_LINE_PATTERNS):
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def sanitize_generated_answer(question: str, answer: str) -> str:
    cleaned = _clean_common(answer, preserve_newlines=True)
    cleaned = remove_meta_scaffolding(cleaned)
    cleaned = re.sub(
        r"^\s*(?:Based on the available documents:|\u0628\u062d\u0633\u0628\s+\u0627\u0644\u0648\u062b\u0627\u0626\u0642\s+\u0627\u0644\u0645\u062a\u0627\u062d\u0629:)\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    if not cleaned:
        return cleaned

    if looks_arabic(question):
        cleaned = _HANGUL_RE.sub(" ", cleaned)
        cleaned = _CYRILLIC_RE.sub(" ", cleaned)
        # Remove duplicated "Term (Term)" artifacts.
        cleaned = re.sub(r"\b([A-Za-z][A-Za-z0-9 ]{2,})\s*\(\1\)", r"\1", cleaned, flags=re.IGNORECASE)

    cleaned = _clean_common(cleaned, preserve_newlines=True)
    cleaned = re.sub(r"\s+([,;:.!?])", r"\1", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()

    # Remove echoed short question prefix at answer start (common OCR/LLM artifact).
    qmark_idx = cleaned.find("?")
    if 3 <= qmark_idx <= 70 and (len(cleaned) - qmark_idx) >= 18:
        prefix = cleaned[: qmark_idx + 1].strip()
        if re.fullmatch(r"[A-Za-z0-9 _'\"\-:/\u0600-\u06FF]{3,}\?", prefix) and _QUESTION_PREFIX_RE.search(prefix):
            cleaned = cleaned[qmark_idx + 1 :].strip()

    has_sql = bool(_SQL_KEYWORD_RE.search(cleaned))
    non_empty_lines = [ln.strip() for ln in cleaned.split("\n") if ln.strip()]
    structured_multiline = (
        len(non_empty_lines) >= 3
        and (
            has_sql
            or any(_LIST_LINE_RE.search(ln) for ln in non_empty_lines)
            or cleaned.count(";") >= 3
        )
    )

    if "\n" in cleaned and not structured_multiline:
        # Keep one compact paragraph for normal chat answers.
        cleaned = " ".join(part.strip() for part in cleaned.split("\n") if part.strip())
        cleaned = _clean_common(cleaned, preserve_newlines=False)
    elif structured_multiline:
        cleaned = "\n".join(non_empty_lines)

    # Normalize semicolon-heavy OCR/generation output into regular sentence flow.
    if cleaned.count(";") >= 2 and not has_sql:
        cleaned = cleaned.replace("; ", ". ").replace(";", ".")
    if has_sql:
        cleaned = re.sub(r"\.\s*;", ";", cleaned)
        cleaned = re.sub(r";\s*\.", ";", cleaned)
    if cleaned.count("\u061B") >= 2 and cleaned.count("طŒ") == 0:
        cleaned = cleaned.replace("\u061B ", "طŒ ").replace("\u061B", "طŒ")

    # If generation stopped mid-sentence, trim to the last complete delimiter.
    # Keep semicolon-separated lists intact to avoid dropping trailing points.
    has_list_structure = structured_multiline or ((cleaned.count(";") + cleaned.count("\u061B")) >= 2)
    if cleaned and cleaned[-1] not in ".!?;\u061F" and not has_list_structure and not has_sql:
        cut = max(
            cleaned.rfind(";"),
            cleaned.rfind("."),
            cleaned.rfind("?"),
            cleaned.rfind("!"),
            cleaned.rfind("\u061F"),
        )
        if cut > int(len(cleaned) * 0.30):
            cleaned = cleaned[: cut + 1].strip()

    # Drop dangling trailing list markers like "6." with no following text.
    cleaned = re.sub(r"(?:\s|^)\d{1,2}\.\s*$", "", cleaned).strip()

    return cleaned


def dedupe_by_normalized_text(values: Iterable[str]) -> list[str]:
    seen = set()
    unique: list[str] = []
    for value in values:
        key = normalize_for_search(value)
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(value)
    return unique
