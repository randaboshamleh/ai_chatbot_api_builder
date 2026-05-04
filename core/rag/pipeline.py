import hashlib
import logging
import os
import re
import threading
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Set, Tuple

from django.conf import settings
from django.core.cache import cache

try:
    import ollama

    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    ollama = None

from core.rag.vector_store import TenantVectorStore
from core.rag.text_preprocessing import (
    normalize_document_text,
    normalize_for_search,
    normalize_user_query,
    sanitize_generated_answer,
)

logger = logging.getLogger(__name__)

RAG_PROMPT_TEMPLATE = """You are Assistify AI, a professional customer support assistant.
Your role is to extract answers accurately using ONLY the provided company documents.
You MUST always answer in the exact same language as the user's question. If the user asks in Arabic, you MUST write your entire response in Arabic, even if the provided context documents are in English. Translate the necessary information from the context into Arabic before responding.

## Core Rules:
- Use ONLY the provided context.
- Never invent facts.
- If the answer is not explicitly in context, respond with NO_INFO.

## Language Rules:
- Detect question language first.
- Reply in the same language.
- For Arabic questions:
  - Write in clear Arabic script only.
  - Do NOT transliterate Arabic words into Latin letters.
  - Keep only unavoidable technical terms (product names/acronyms) in English exactly as written in context.
- For English questions:
  - Reply in natural English.

## Source Accuracy Rules:
- Prioritize the most relevant details.
- If multiple sources conflict, pick the most directly matching chunk.
- Do not answer from unrelated chunks.

## Extraction Rules (STRICT):
- Extract and return the EXACT text from the context that answers the question.
- Do NOT summarize, shorten, or rephrase the text. Quote it directly as it appears in the source.
- Do NOT change the formatting of the original text (e.g., if the context is a paragraph, return a paragraph; if it's a list, return a list).
- If the answer spans multiple distinct sentences or paragraphs in the context, extract all of them exactly as written.
- Do NOT include meta phrases like "Here is the answer", "Note:", or translation disclaimers.
- Start with the exact extracted answer immediately.

Context:
{context}

Question: {question}

Answer:"""

SUMMARY_PROMPT = """Summarize the following text in 2-3 concise sentences. Focus on the key information only.

Text:
{text}

Summary:"""

MIN_RELEVANCE_SCORE = 0.45
RESULT_CACHE_VERSION = "v4"

QUERY_REWRITE_PROMPT = """Rewrite the user question to optimize retrieval from company documents.
Rules:
- Preserve the original intent exactly.
- Keep product names and technical terms unchanged.
- Keep the same language as the user question.
- Do not add any new facts or assumptions.
- Return only the rewritten query text.

User question:
{question}

Rewritten query:"""

CROSS_LANGUAGE_QUERY_HINT_PROMPT = """Convert the user query into short English retrieval keywords.
Rules:
- Preserve the original intent exactly.
- Do not add new facts.
- Keep names/acronyms exactly when present.
- Return one short line of English keywords only.

User query:
{question}

English retrieval keywords:"""

SELF_CHECK_PROMPT = """You are a strict answer auditor.
Decide if the answer is fully supported by the provided context only.
Return exactly one line in this format:
VERDICT: YES|NO | REASON: <short reason>

Context:
{context}

Question:
{question}

Answer:
{answer}
"""

TOKEN_RE = re.compile(r"[A-Za-z0-9_]+|[\u0600-\u06FF]+")
MIXED_SCRIPT_RE = re.compile(r"(?:[\u0600-\u06FF][A-Za-z])|(?:[A-Za-z][\u0600-\u06FF])")
CORRUPTED_ARABIC_QUERY_RE = re.compile(r"^\s*(?:\?\s*){2,}[A-Za-z0-9 _\-\?]*$", re.IGNORECASE)
ABSTENTION_PATTERNS = [
    re.compile(r"\bNO_INFO\b", re.IGNORECASE),
    re.compile(r"\bi could not find\b", re.IGNORECASE),
    re.compile(r"\bnot (?:explicitly )?in (?:the )?context\b", re.IGNORECASE),
    re.compile(r"\bno(?: clear)? answer\b", re.IGNORECASE),
    re.compile(r"\binsufficient (?:context|information)\b", re.IGNORECASE),
    re.compile(r"\u0644\u0645\s*\u0623?\u062c\u062f\s*\u0625?\u062c\u0627\u0628\u0629", re.IGNORECASE),
    re.compile(r"\u0644\u0627\s*\u062a\u0648\u062c\u062f\s*\u0625?\u062c\u0627\u0628\u0629", re.IGNORECASE),
    re.compile(r"\u0644\u0627\s*\u0623?\u0633\u062a\u0637\u064a\u0639\s*\u0627\u0644\u0625\u062c\u0627\u0628\u0629", re.IGNORECASE),
    re.compile(r"\u0644\u0627\s*\u062a\u062a\u0648\u0641\u0631\s*\u0645\u0639\u0644\u0648\u0645\u0627\u062a", re.IGNORECASE),
    re.compile(r"\b\u0644\u0627 (?:\u062a\u0648\u062c\u062f|\u064a\u0648\u062c\u062f)\s+\u0645\u0639\u0644\u0648\u0645\u0629\b", re.IGNORECASE),
    re.compile(r"\b\u0644\u0645\s+\u0623\u062c\u062f\s+\u0625\u062c\u0627\u0628\u0629\b", re.IGNORECASE),
    re.compile(r"\b\u0644\u0627\s+\u0623\u0633\u062a\u0637\u064a\u0639\s+\u0627\u0644\u0625\u062c\u0627\u0628\u0629\b", re.IGNORECASE),
    re.compile(r"\b\u063a\u064a\u0631\s+\u0645\u062a(?:\u0648\u0641\u0631|\u0627\u062d\u0629)\b", re.IGNORECASE),
]
ABSTENTION_SUBSTRINGS = [
    "\u0644\u0645 \u0623\u062c\u062f \u0625\u062c\u0627\u0628\u0629 \u0648\u0627\u0636\u062d\u0629",
    "\u0644\u0645 \u0627\u062c\u062f \u0627\u062c\u0627\u0628\u0629 \u0648\u0627\u0636\u062d\u0629",
    "\u0644\u0627 \u062a\u0648\u062c\u062f \u0625\u062c\u0627\u0628\u0629 \u0648\u0627\u0636\u062d\u0629",
    "\u0644\u0627 \u062a\u0648\u062c\u062f \u0627\u062c\u0627\u0628\u0629 \u0648\u0627\u0636\u062d\u0629",
    "\u0644\u0627 \u064a\u0648\u062c\u062f \u062c\u0648\u0627\u0628 \u0648\u0627\u0636\u062d",
    "\u0644\u0627 \u0623\u0633\u062a\u0637\u064a\u0639 \u0627\u0644\u0625\u062c\u0627\u0628\u0629 \u0628\u0646\u0627\u0621",
    "\u0644\u0627 \u0627\u0633\u062a\u0637\u064a\u0639 \u0627\u0644\u0627\u062c\u0627\u0628\u0629 \u0628\u0646\u0627\u0621",
    "\u0644\u0627 \u062a\u062a\u0648\u0641\u0631 \u0645\u0639\u0644\u0648\u0645\u0627\u062a \u0643\u0627\u0641\u064a\u0629",
    "\u063a\u064a\u0631 \u0645\u062a\u0627\u062d\u0629 \u0641\u064a \u0627\u0644\u0648\u062b\u0627\u0626\u0642",
    "i could not find a clear answer",
    "no clear answer in the available documents",
    "insufficient information in the context",
]
STREAM_CONTROL_CHARS_RE = re.compile(r"[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F-\u009F]")
STREAM_ZERO_WIDTH_RE = re.compile(r"[\u200B-\u200F\uFEFF\u2066-\u2069]")
STREAM_REPLACEMENT_RE = re.compile(r"[\uFFFD]")
STREAM_NOISE_SYMBOLS_RE = re.compile(r"[\u25A0-\u25FF\u2600-\u26FF\u2700-\u27BF\uE000-\uF8FF]")
STREAM_MULTI_SPACE_RE = re.compile(r"[ \t\f\v]{2,}")
DEFINITION_QUERY_RE = re.compile(
    r"(?:\bwhat\s+is\b|\bwho\s+is\b|\bdefine\b|\boverview\b|\bmeaning\b|\bexplain(?:ation)?\b|(?:^|\s)\u0645\u0627\s+\u0647\u0648(?:\s|$)|(?:^|\s)\u0645\u0627\s+\u0647\u064a(?:\s|$)|(?:^|\s)\u0645\u0646\s+\u0647\u0648(?:\s|$)|(?:^|\s)\u062a\u0639\u0631\u064a\u0641(?:\s|$)|(?:^|\s)\u0646\u0628\u0630\u0629(?:\s|$)|(?:^|\s)\u0627\u0634\u0631\u062d(?:\s|$)|(?:^|\s)\u0634\u0631\u062d(?:\s|$))",
    flags=re.IGNORECASE,
)
DEFINITION_TEXT_HINT_RE = re.compile(
    r"(?:\bis\s+(?:a|an|the)\b|\brefers\s+to\b|\bdefined\s+as\b|\bplatform\b|\btool\b|(?:^|\s)\u0647\u0648(?:\s|$)|(?:^|\s)\u0647\u064a(?:\s|$)|(?:^|\s)\u0639\u0628\u0627\u0631\u0629\s+\u0639\u0646(?:\s|$)|(?:^|\s)\u0623\u062f\u0627\u0629(?:\s|$))",
    flags=re.IGNORECASE,
)
PROCEDURAL_TEXT_HINT_RE = re.compile(
    r"(?:\binstall(?:ation)?\b|\bdownload\b|\bsetup\b|\bconfigure\b|\bverify\b|\bextract\b|\bcreate\s+account\b|\brequirements?\b|\bstep(?:s)?\b|(?:^|\s)\u062a\u062b\u0628\u064a\u062a(?:\s|$)|(?:^|\s)\u062a\u0646\u0632\u064a\u0644(?:\s|$)|(?:^|\s)\u0625\u0639\u062f\u0627\u062f(?:\s|$)|(?:^|\s)\u062e\u0637\u0648\u0629(?:\s|$)|(?:^|\s)\u0645\u062a\u0637\u0644\u0628\u0627\u062a(?:\s|$)|(?:^|\s)\u0642\u0645\s+\u0628(?:\s|$))",
    flags=re.IGNORECASE,
)
MULTI_POINT_QUERY_RE = re.compile(
    r"(?:\b(?:why|reasons?|benefits?|advantages?|features?|key\s+points?|steps?|explain(?:ation)?)\b|(?:^|\s)\u0644\u0645\u0627\u0630\u0627(?:\s|$)|(?:^|\s)\u0627\u0633\u0628\u0627\u0628(?:\s|$)|(?:^|\s)\u0627\u0644\u0627\u0633\u0628\u0627\u0628(?:\s|$)|(?:^|\s)\u0641\u0648\u0627\u0626\u062f(?:\s|$)|(?:^|\s)\u0645\u0632\u0627\u064a\u0627(?:\s|$)|(?:^|\s)\u0645\u062d\u0627\u0648\u0631(?:\s|$)|(?:^|\s)\u0646\u0642\u0627\u0637(?:\s|$)|(?:^|\s)\u062e\u0637\u0648\u0627\u062a(?:\s|$)|(?:^|\s)\u0627\u0634\u0631\u062d(?:\s|$)|(?:^|\s)\u0634\u0631\u062d(?:\s|$))",
    flags=re.IGNORECASE,
)
WHY_USE_QUERY_RE = re.compile(
    r"(?:\bwhy\s+use\b|(?:^|\s)\u0644\u0645\u0627\u0630\u0627\s+\u0646\u0633\u062a\u062e\u062f\u0645(?:\s|$)|(?:^|\s)\u0644\u0645\u0627\u0630\u0627\s+\u0646\u0633\u062a\u0639\u0645\u0644(?:\s|$))",
    flags=re.IGNORECASE,
)
WHY_QUERY_RE = re.compile(
    r"(?:\bwhy\b|(?:^|\s)\u0644\u0645\u0627\u0630\u0627(?:\s|$)|(?:^|\s)\u0644\u064a\u0634(?:\s|$))",
    flags=re.IGNORECASE,
)
HOW_QUERY_RE = re.compile(
    r"(?:\bhow(?:\s+to)?\b|(?:^|\s)\u0643\u064a\u0641(?:\s|$)|(?:^|\s)\u0634\u0648\u0646(?:\s|$))",
    flags=re.IGNORECASE,
)
WHEN_QUERY_RE = re.compile(
    r"(?:\bwhen\b|(?:^|\s)\u0645\u062a\u0649(?:\s|$)|(?:^|\s)\u0627\u0645\u062a\u0649(?:\s|$)|(?:^|\s)\u062a\u0627\u0631\u064a\u062e(?:\s|$))",
    flags=re.IGNORECASE,
)
WHO_QUERY_RE = re.compile(
    r"(?:\bwho\b|(?:^|\s)\u0645\u0646(?:\s|$)|(?:^|\s)\u0645\u0646\s+\u0647\u0648(?:\s|$)|(?:^|\s)\u0645\u0646\s+\u0647\u064a(?:\s|$))",
    flags=re.IGNORECASE,
)
WHERE_QUERY_RE = re.compile(
    r"(?:\bwhere\b|(?:^|\s)\u0627\u064a\u0646(?:\s|$)|(?:^|\s)\u0623\u064a\u0646(?:\s|$)|(?:^|\s)\u0648\u064a\u0646(?:\s|$))",
    flags=re.IGNORECASE,
)
WHICH_QUERY_RE = re.compile(
    r"(?:\bwhich\b|(?:^|\s)\u0623?\u064a(?:\s|$)|(?:^|\s)\u0623?\u064a\u0647\u0645\u0627(?:\s|$))",
    flags=re.IGNORECASE,
)
QUANTITY_QUERY_RE = re.compile(
    r"(?:\bhow\s+(?:many|much)\b|(?:^|\s)\u0643\u0645(?:\s|$)|(?:^|\s)\u0639\u062f\u062f(?:\s|$)|(?:^|\s)\u0646\u0633\u0628\u0629(?:\s|$)|(?:^|\s)\u062a\u0643\u0644\u0641\u0629(?:\s|$)|(?:^|\s)\u0633\u0639\u0631(?:\s|$))",
    flags=re.IGNORECASE,
)
CAPABILITY_QUERY_RE = re.compile(
    r"(?:\bcan\b|\bdoes\b.*\bsupport\b|(?:^|\s)\u0647\u0644\s+\u064a\u0645\u0643\u0646(?:\s|$)|(?:^|\s)\u0647\u0644\s+\u064a\u062f\u0639\u0645(?:\s|$)|(?:^|\s)\u064a\u062f\u0639\u0645(?:\s|$))",
    flags=re.IGNORECASE,
)
WHY_CHOOSE_TEXT_RE = re.compile(
    r"(?:\bwhy\s+choose\b|(?:^|\s)\u0644\u0645\u0627\u0630\u0627\s+\u062a\u062e\u062a\u0627\u0631(?:\s|$))",
    flags=re.IGNORECASE,
)
PROCEDURAL_STEP_HINT_RE = re.compile(
    r"(?:^\s*(?:step|steps?)\b|^\s*\d{1,2}[\)\.\-]\s+|\bclick\b|\bopen\b|\bupload\b|\bselect\b|\bconfigure\b|\binstall\b|(?:^|\s)\u062e\u0637\u0648\u0629(?:\s|$)|(?:^|\s)\u0627\u0636\u063a\u0637(?:\s|$)|(?:^|\s)\u0627\u0641\u062a\u062d(?:\s|$)|(?:^|\s)\u0627\u0631\u0641\u0639(?:\s|$)|(?:^|\s)\u0627\u062e\u062a\u0631(?:\s|$)|(?:^|\s)\u062b\u0628\u062a(?:\s|$))",
    flags=re.IGNORECASE,
)
TEMPORAL_TEXT_HINT_RE = re.compile(
    r"(?:\b(?:date|time|year|month|day|deadline|schedule|today|tomorrow|yesterday)\b|\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|\b\d{4}\b|(?:^|\s)\u062a\u0627\u0631\u064a\u062e(?:\s|$)|(?:^|\s)\u0645\u0648\u0639\u062f(?:\s|$)|(?:^|\s)\u0627\u0644\u064a\u0648\u0645(?:\s|$)|(?:^|\s)\u063a\u062f(?:\s|$)|(?:^|\s)\u0623\u0645\u0633(?:\s|$)|(?:^|\s)\u0633\u0627\u0639\u0629(?:\s|$))",
    flags=re.IGNORECASE,
)
PERSON_TEXT_HINT_RE = re.compile(
    r"(?:\b(?:presented by|author|founder|created by|developed by|speaker|instructor)\b|(?:^|\s)\u0642\u062f\u0645(?:\s|$)|(?:^|\s)\u0645\u0624\u0644\u0641(?:\s|$)|(?:^|\s)\u0628\u0648\u0627\u0633\u0637\u0629(?:\s|$)|(?:^|\s)\u0625\u0639\u062f\u0627\u062f(?:\s|$))",
    flags=re.IGNORECASE,
)
LOCATION_TEXT_HINT_RE = re.compile(
    r"(?:\b(?:location|address|country|city|university|headquarters|based in)\b|(?:^|\s)\u0645\u0648\u0642\u0639(?:\s|$)|(?:^|\s)\u0639\u0646\u0648\u0627\u0646(?:\s|$)|(?:^|\s)\u062c\u0627\u0645\u0639\u0629(?:\s|$)|(?:^|\s)\u0645\u062f\u064a\u0646\u0629(?:\s|$)|(?:^|\s)\u062f\u0648\u0644\u0629(?:\s|$))",
    flags=re.IGNORECASE,
)
QUANTITY_TEXT_HINT_RE = re.compile(
    r"(?:\b\d+(?:\.\d+)?\s*(?:%|percent|usd|eur|\$)\b|\b(?:price|cost|total|count|number|amount)\b|(?:^|\s)\u0633\u0639\u0631(?:\s|$)|(?:^|\s)\u062a\u0643\u0644\u0641\u0629(?:\s|$)|(?:^|\s)\u0639\u062f\u062f(?:\s|$)|(?:^|\s)\u0646\u0633\u0628\u0629(?:\s|$)|(?:^|\s)\u0643\u0645(?:\s|$))",
    flags=re.IGNORECASE,
)
CAPABILITY_TEXT_HINT_RE = re.compile(
    r"(?:\b(?:supports?|compatible|available|can|ability|capable)\b|(?:^|\s)\u064a\u062f\u0639\u0645(?:\s|$)|(?:^|\s)\u0645\u062a\u0627\u062d(?:\s|$)|(?:^|\s)\u064a\u0645\u0643\u0646(?:\s|$)|(?:^|\s)\u0642\u0627\u062f\u0631(?:\s|$))",
    flags=re.IGNORECASE,
)
CHOICE_TEXT_HINT_RE = re.compile(
    r"(?:\b(?:option|options|compare|comparison|vs|versus|best|choose)\b|(?:^|\s)\u062e\u064a\u0627\u0631(?:\s|$)|(?:^|\s)\u0645\u0642\u0627\u0631\u0646\u0629(?:\s|$)|(?:^|\s)\u0627\u0641\u0636\u0644(?:\s|$)|(?:^|\s)\u0627\u062e\u062a\u064a\u0627\u0631(?:\s|$))",
    flags=re.IGNORECASE,
)
LIMITATION_QUERY_RE = re.compile(
    r"(?:\b(?:limitations?|challenges?|drawbacks?|cons?|weaknesses?|disadvantages?)\b|(?:^|\s)\u0642\u064a\u0648\u062f(?:\s|$)|(?:^|\s)\u062a\u062d\u062f\u064a\u0627\u062a(?:\s|$)|(?:^|\s)\u0639\u064a\u0648\u0628(?:\s|$)|(?:^|\s)\u0633\u0644\u0628\u064a\u0627\u062a(?:\s|$))",
    flags=re.IGNORECASE,
)
POSITIVE_SECTION_HINT_RE = re.compile(
    r"(?:\b(?:benefits?|advantages?|features?|reasons?|why\s+use)\b|(?:^|\s)\u0641\u0648\u0627\u0626\u062f(?:\s|$)|(?:^|\s)\u0645\u0632\u0627\u064a\u0627(?:\s|$)|(?:^|\s)\u0623\u0633\u0628\u0627\u0628(?:\s|$))",
    flags=re.IGNORECASE,
)
NEGATIVE_SECTION_HINT_RE = re.compile(
    r"(?:\b(?:limitations?|challenges?|drawbacks?|cons?|considerations?|weaknesses?|disadvantages?)\b|(?:^|\s)\u0642\u064a\u0648\u062f(?:\s|$)|(?:^|\s)\u062a\u062d\u062f\u064a\u0627\u062a(?:\s|$)|(?:^|\s)\u0639\u064a\u0648\u0628(?:\s|$)|(?:^|\s)\u0633\u0644\u0628\u064a\u0627\u062a(?:\s|$))",
    flags=re.IGNORECASE,
)
AR_QUERY_EXPANSIONS: List[Tuple[re.Pattern[str], Tuple[str, ...]]] = [
    (re.compile(r"(?:\u0627\u062a\u0645\u062a\u0629|\u0627\u0644\u0627\u0644\u064a|\u0627\u0644\u0627\u0644\u064a\u0629)"), ("automation", "automated")),
    (re.compile(r"(?:\u0627\u062e\u062a\u0628\u0627\u0631|\u0627\u062e\u062a\u0628\u0627\u0631\u0627\u062a)"), ("test", "testing", "qa", "quality")),
    (re.compile(r"(?:\u0627\u062f\u0627\u0629|\u0627\u062f\u0648\u0627\u062a)"), ("tool", "tools")),
    (re.compile(r"(?:\u0627\u0633\u062a\u062e\u062f\u0627\u0645|\u0646\u0633\u062a\u062e\u062f\u0645)"), ("use", "usage", "adoption")),
    (re.compile(r"(?:\u0633\u0639\u0631|\u0627\u0633\u0639\u0627\u0631|\u062a\u0643\u0644\u0641\u0629|\u0627\u0634\u062a\u0631\u0627\u0643)"), ("price", "pricing", "cost", "subscription")),
    (re.compile(r"(?:\u0645\u064a\u0632\u0629|\u0645\u064a\u0632\u0627\u062a|\u0645\u0632\u0627\u064a\u0627|\u062e\u0627\u0635\u064a\u0629)"), ("features", "capabilities", "functions")),
    (re.compile(r"(?:\u062f\u0639\u0645|\u0645\u0633\u0627\u0639\u062f\u0629|\u0645\u0634\u0643\u0644\u0629|\u062e\u0637\u0623)"), ("support", "help", "issue", "error", "troubleshooting")),
    (re.compile(r"(?:\u062a\u062b\u0628\u064a\u062a|\u0627\u0639\u062f\u0627\u062f|\u062a\u0634\u063a\u064a\u0644|\u0628\u062f\u0621)"), ("install", "setup", "configuration", "start")),
    (re.compile(r"(?:\u0645\u0627\u0647\u0648|\u0645\u0627\u0647\u064a|\u062a\u0639\u0631\u064a\u0641)"), ("what is", "definition", "overview")),
    (re.compile(r"(?:\u0644\u0645\u0627\u0630\u0627|\u0644\u064a\u0634)"), ("why", "reason")),
    (re.compile(r"(?:\u0628\u0631\u0648\u0641\u0627\u064a\u0644|\u0628\u0631\u0648\u0641\u0627\u064a\u0644\u0627\u062a|\u0628\u0631\u0648\u0641\u0627\u064a\u0644\u0627\u062a)"), ("profile", "profiles", "policy", "policies")),
    (re.compile(r"(?:\u0633\u064a\u0627\u0633\u0629|\u0633\u064a\u0627\u0633\u0627\u062a)"), ("policy", "policies", "rules", "settings")),
    (re.compile(r"(?:\u0646\u062a\u0627\u0626\u062c|\u0646\u062a\u064a\u062c\u0629)"), ("result", "results", "outcome", "report")),
    (re.compile(r"(?:\u062e\u0644\u0627\u0635\u0629|\u0627\u0633\u062a\u0646\u062a\u0627\u062c|\u062e\u0627\u062a\u0645\u0629)"), ("summary", "conclusion", "final notes")),
]
SELF_CHECK_VERDICT_RE = re.compile(r"VERDICT:\s*(YES|NO)\b", flags=re.IGNORECASE)
SENTENCE_SPLIT_RE = re.compile(r"(?<=[\.\!\?\u061F])\s+")
HEADING_UPPER_RE = re.compile(r"^[A-Z][A-Z\s\-:&/]{5,}$")
HEADING_TITLE_RE = re.compile(
    r"^(?:Introduction|Overview|Advantages|Features|Interface|Conclusion)\b",
    flags=re.IGNORECASE,
)
HEADING_PHRASE_RE = re.compile(
    r"(?:\bwhy\s+use\b|\bbenefits?\b|\badvantages?\b|\bkey\s+features?\b|\boverview\b)",
    flags=re.IGNORECASE,
)
ACTION_SENTENCE_RE = re.compile(
    r"(?:\bincreas(?:e|es|ed|ing)\b|\breduc(?:e|es|ed|ing)\b|\bsav(?:e|es|ed|ing)\b|\benabl(?:e|es|ed|ing)\b|\bimprov(?:e|es|ed|ing)\b|\bsupport(?:s|ed|ing)?\b|\bprovid(?:e|es|ed|ing)\b|\ballow(?:s|ed|ing)?\b|\bhelp(?:s|ed|ing)?\b|\bboost(?:s|ed|ing)?\b|\benhanc(?:e|es|ed|ing)\b|\baccelerat(?:e|es|ed|ing)\b|\bminimiz(?:e|es|ed|ing)\b|(?:^|\s)\u064a\u0632\u064a\u062f(?:\s|$)|(?:^|\s)\u064a\u0642\u0644\u0644(?:\s|$)|(?:^|\s)\u064a\u0648\u0641\u0631(?:\s|$)|(?:^|\s)\u064a\u0633\u0627\u0639\u062f(?:\s|$)|(?:^|\s)\u064a\u062d\u0633\u0646(?:\s|$))",
    flags=re.IGNORECASE,
)
STARTS_WITH_ACTION_RE = re.compile(
    r"^(?:increases?|reduces?|saves?|enables?|improves?|supports?|provides?|allows?|boosts?|enhances?|accelerates?|minimizes?)\b|^(?:\u064a\u0632\u064a\u062f|\u064a\u0642\u0644\u0644|\u064a\u0648\u0641\u0631|\u064a\u0633\u0627\u0639\u062f|\u064a\u062d\u0633\u0646)\b",
    flags=re.IGNORECASE,
)
NOISY_OCR_LINE_RE = re.compile(
    r"(?:[a-z][A-Z]{3,}|[A-Z]{4,}\s+[A-Z]{4,}\s+[A-Z]{4,}|[A-Za-z]{18,})"
)
CONTINUATION_LINE_RE = re.compile(
    r"^(?:and|or|to|with|for|by|via|through|using|allowing|including|improving|enhancing|ensuring|which)\b",
    flags=re.IGNORECASE,
)
URL_RE = re.compile(r"(?:https?://[^\s\]\)]+|www\.[^\s\]\)]+)", flags=re.IGNORECASE)
SQL_TECHNICAL_RE = re.compile(
    r"\b(?:CREATE|GRANT|ALTER|DROP|INSERT|UPDATE|DELETE|SELECT|TABLESPACE|PROFILE|ROLE|USER)\b",
    flags=re.IGNORECASE,
)
SECTION_HEADING_LINE_RE = re.compile(
    r"^\s*\d{1,2}\.\s+(?:[A-Za-z][A-Za-z0-9 _\-/]{1,80}|[\u0600-\u06FF][\u0600-\u06FF0-9 _\-/]{1,80})\s*$",
    flags=re.IGNORECASE,
)
PROMPT_LEAK_RE = re.compile(
    r"(?:if the input is a list|keep the same list structure|do not add facts|return arabic answer text only|"
    r"keep .*sql.* as[-\s]?is|^\s*\*+\s*text\s*:\s*\*+|^\s*text\s*:|^\s*arabic\s*:|"
    r"إذا كان الإدخال|لا تضف أي حقائق|احتفظ .*SQL|أرجع النص العربي)",
    flags=re.IGNORECASE | re.MULTILINE,
)
SECTION_BREAK_RE = re.compile(
    r"(?:^\s*(?:introduction|overview|advantages|features|conclusion)\b|^\s*(?:\u0645\u0642\u062f\u0645\u0629|\u0646\u0628\u0630\u0629|\u0627\u0644\u0645\u0632\u0627\u064a\u0627|\u0627\u0644\u062e\u0635\u0627\u0626\u0635)\b)",
    flags=re.IGNORECASE,
)
TOPIC_CAPTURE_PATTERNS = [
    re.compile(r"\bwhat\s+is\s+(.+)$", re.IGNORECASE),
    re.compile(r"\bwho\s+is\s+(.+)$", re.IGNORECASE),
    re.compile(r"\bdefine\s+(.+)$", re.IGNORECASE),
    re.compile(r"(?:^|\s)\u0645\u0627\s+\u0647\u0648\s+(.+)$", re.IGNORECASE),
    re.compile(r"(?:^|\s)\u0645\u0627\s+\u0647\u064a\s+(.+)$", re.IGNORECASE),
    re.compile(r"(?:^|\s)\u0645\u0646\s+\u0647\u0648\s+(.+)$", re.IGNORECASE),
]

AR_STOPWORDS: Set[str] = {
    "\u0645\u0646", "\u0627\u0644\u0649", "\u0625\u0644\u0649", "\u0639\u0644\u0649", "\u0641\u064a", "\u0639\u0646", "\u0645\u0627", "\u0645\u0627\u0630\u0627", "\u0647\u0644", "\u0643\u064a\u0641", "\u0643\u0645", "\u0644\u0645\u0627\u0630\u0627", "\u0627\u0630\u0627", "\u0625\u0630\u0627",
    "\u0647\u0630\u0627", "\u0647\u0630\u0647", "\u0630\u0644\u0643", "\u062a\u0644\u0643", "\u0647\u0646\u0627\u0643", "\u0645\u0639", "\u0623\u0648", "\u0627\u0648", "\u062b\u0645", "\u0644\u0642\u062f", "\u062a\u0645", "\u0647\u064a", "\u0647\u0648", "\u0647\u0645", "\u0647\u0646",
}

EN_STOPWORDS: Set[str] = {
    "the", "a", "an", "is", "are", "was", "were", "to", "of", "in", "on", "for", "from", "with", "at",
    "by", "and", "or", "as", "be", "can", "could", "should", "would", "what", "how", "when", "where",
    "why", "which", "that", "this", "these", "those",
}

GENERIC_QUERY_TOKENS: Set[str] = {
    "what", "why", "how", "when", "where", "which", "who",
    "feature", "features", "benefit", "benefits", "advantages",
    "tool", "tools", "platform", "software", "system",
    "support", "help", "issue", "problem", "error",
    "price", "pricing", "cost", "plan", "plans",
    "details", "detail", "information", "about", "overview",
}

INTENT_KEYWORDS = {
    "pricing": ["price", "pricing", "cost", "plan", "plans", "subscription", "fee", "payment", "billing", "discount", "package", "tier", "\u0633\u0639\u0631", "\u0623\u0633\u0639\u0627\u0631", "\u062a\u0643\u0644\u0641\u0629", "\u062e\u0637\u0629", "\u0627\u0634\u062a\u0631\u0627\u0643"],
    "features": ["feature", "features", "integration", "dashboard", "api", "capability", "function", "tool", "\u0645\u064a\u0632\u0629", "\u0645\u064a\u0632\u0627\u062a", "\u062a\u0643\u0627\u0645\u0644", "\u0644\u0648\u062d\u0629", "\u0623\u062f\u0627\u0629"],
    "support": ["support", "help", "contact", "faq", "issue", "problem", "error", "bug", "how", "guide", "\u062f\u0639\u0645", "\u0645\u0633\u0627\u0639\u062f\u0629", "\u0645\u0634\u0643\u0644\u0629", "\u062e\u0637\u0623", "\u0643\u064a\u0641"],
    "onboarding": ["start", "setup", "install", "configure", "register", "signup", "getting", "\u0628\u062f\u0621", "\u0625\u0639\u062f\u0627\u062f", "\u062a\u0633\u062c\u064a\u0644"],
}


@dataclass
class StreamAnswerState:
    tokens: List[str] = field(default_factory=list)
    final_answer: str = ""

    @property
    def raw_answer(self) -> str:
        return "".join(self.tokens)


class RAGPipeline:
    def __init__(self, tenant):
        self.tenant = tenant
        self.vector_store = TenantVectorStore(str(tenant.id))

        self.min_relevance_score = float(os.getenv('RAG_MIN_RELEVANCE_SCORE', getattr(settings, 'RAG_MIN_RELEVANCE_SCORE', MIN_RELEVANCE_SCORE)))
        self.retrieval_k = max(4, int(os.getenv('RAG_RETRIEVAL_K', getattr(settings, 'RAG_RETRIEVAL_K', 8))))
        self.max_detail_chunks = max(2, int(os.getenv('RAG_MAX_DETAIL_CHUNKS', getattr(settings, 'RAG_MAX_DETAIL_CHUNKS', 4))))
        self.max_context_chars = max(1000, int(os.getenv('RAG_MAX_CONTEXT_CHARS', getattr(settings, 'RAG_MAX_CONTEXT_CHARS', 2200))))

        self.query_cache_ttl = max(0, int(os.getenv('RAG_QUERY_CACHE_TTL_SECONDS', getattr(settings, 'RAG_QUERY_CACHE_TTL_SECONDS', 90))))
        self.summary_cache_ttl = max(0, int(os.getenv('RAG_SUMMARY_CACHE_TTL_SECONDS', getattr(settings, 'RAG_SUMMARY_CACHE_TTL_SECONDS', 300))))

        self.enable_keyword_search = os.getenv('RAG_ENABLE_KEYWORD_SEARCH', str(getattr(settings, 'RAG_ENABLE_KEYWORD_SEARCH', True))).lower() == 'true'
        self.keyword_min_query_length = max(2, int(os.getenv('RAG_KEYWORD_MIN_QUERY_LENGTH', getattr(settings, 'RAG_KEYWORD_MIN_QUERY_LENGTH', 4))))
        self.keyword_fallback_threshold = float(os.getenv('RAG_KEYWORD_FALLBACK_THRESHOLD', getattr(settings, 'RAG_KEYWORD_FALLBACK_THRESHOLD', 0.72)))
        self.answer_mode = os.getenv('RAG_ANSWER_MODE', getattr(settings, 'RAG_ANSWER_MODE', 'extractive')).strip().lower()
        if self.answer_mode not in {'extractive', 'hybrid', 'generative'}:
            self.answer_mode = 'extractive'
        self.strict_extractive_line_overlap = float(
            os.getenv(
                'RAG_STRICT_EXTRACTIVE_LINE_OVERLAP',
                getattr(settings, 'RAG_STRICT_EXTRACTIVE_LINE_OVERLAP', 0.20),
            )
        )
        self.closest_excerpt_min_score = float(
            os.getenv(
                'RAG_CLOSEST_EXCERPT_MIN_SCORE',
                getattr(settings, 'RAG_CLOSEST_EXCERPT_MIN_SCORE', 0.30),
            )
        )
        self.extractive_enforce_query_language = os.getenv(
            'RAG_EXTRACTIVE_ENFORCE_QUERY_LANGUAGE',
            str(getattr(settings, 'RAG_EXTRACTIVE_ENFORCE_QUERY_LANGUAGE', True)),
        ).lower() == 'true'
        self.extractive_use_llm_rewrite = os.getenv(
            'RAG_EXTRACTIVE_USE_LLM_REWRITE',
            str(getattr(settings, 'RAG_EXTRACTIVE_USE_LLM_REWRITE', False)),
        ).lower() == 'true'
        self.extractive_require_context_sufficient = os.getenv(
            'RAG_EXTRACTIVE_REQUIRE_CONTEXT_SUFFICIENT',
            str(getattr(settings, 'RAG_EXTRACTIVE_REQUIRE_CONTEXT_SUFFICIENT', True)),
        ).lower() == 'true'
        self.extractive_low_conf_top_score = float(
            os.getenv(
                'RAG_EXTRACTIVE_LOW_CONF_TOP_SCORE',
                getattr(settings, 'RAG_EXTRACTIVE_LOW_CONF_TOP_SCORE', 0.52),
            )
        )
        self.extractive_low_conf_overlap = float(
            os.getenv(
                'RAG_EXTRACTIVE_LOW_CONF_OVERLAP',
                getattr(settings, 'RAG_EXTRACTIVE_LOW_CONF_OVERLAP', 0.06),
            )
        )

        self.answer_max_tokens = max(80, int(os.getenv('RAG_ANSWER_MAX_TOKENS', getattr(settings, 'RAG_ANSWER_MAX_TOKENS', 180))))
        self.summary_max_tokens = max(50, int(os.getenv('RAG_SUMMARY_MAX_TOKENS', getattr(settings, 'RAG_SUMMARY_MAX_TOKENS', 150))))
        self.llm_num_ctx = max(512, int(os.getenv('RAG_LLM_NUM_CTX', getattr(settings, 'RAG_LLM_NUM_CTX', 2048))))
        self.llm_temperature = float(os.getenv('RAG_LLM_TEMPERATURE', getattr(settings, 'RAG_LLM_TEMPERATURE', 0.0)))
        self.llm_top_p = float(os.getenv('RAG_LLM_TOP_P', getattr(settings, 'RAG_LLM_TOP_P', 0.9)))
        self.max_response_seconds = max(
            8.0,
            float(os.getenv('RAG_MAX_RESPONSE_SECONDS', getattr(settings, 'RAG_MAX_RESPONSE_SECONDS', 75))),
        )
        self.max_summary_seconds = max(
            6.0,
            float(os.getenv('RAG_MAX_SUMMARY_SECONDS', getattr(settings, 'RAG_MAX_SUMMARY_SECONDS', 45))),
        )
        self.single_document_bias = os.getenv(
            'RAG_SINGLE_DOCUMENT_BIAS',
            str(getattr(settings, 'RAG_SINGLE_DOCUMENT_BIAS', True)),
        ).lower() == 'true'
        self.document_confidence_margin = float(
            os.getenv(
                'RAG_DOCUMENT_CONFIDENCE_MARGIN',
                getattr(settings, 'RAG_DOCUMENT_CONFIDENCE_MARGIN', 0.06),
            )
        )
        self.document_boost_weight = float(
            os.getenv(
                'RAG_DOCUMENT_BOOST_WEIGHT',
                getattr(settings, 'RAG_DOCUMENT_BOOST_WEIGHT', 0.06),
            )
        )
        self.document_density_bonus = float(
            os.getenv(
                'RAG_DOCUMENT_DENSITY_BONUS',
                getattr(settings, 'RAG_DOCUMENT_DENSITY_BONUS', 0.01),
            )
        )
        self.min_chunk_lexical_overlap = float(
            os.getenv(
                'RAG_MIN_CHUNK_LEXICAL_OVERLAP',
                getattr(settings, 'RAG_MIN_CHUNK_LEXICAL_OVERLAP', 0.05),
            )
        )
        self.min_high_conf_semantic = float(
            os.getenv(
                'RAG_MIN_HIGH_CONF_SEMANTIC',
                getattr(settings, 'RAG_MIN_HIGH_CONF_SEMANTIC', 0.74),
            )
        )
        self.anchor_bonus_weight = float(
            os.getenv(
                'RAG_QUERY_ANCHOR_BONUS_WEIGHT',
                getattr(settings, 'RAG_QUERY_ANCHOR_BONUS_WEIGHT', 0.18),
            )
        )
        self.anchor_penalty_weight = float(
            os.getenv(
                'RAG_QUERY_ANCHOR_PENALTY_WEIGHT',
                getattr(settings, 'RAG_QUERY_ANCHOR_PENALTY_WEIGHT', 0.16),
            )
        )
        self.context_score_margin = float(
            os.getenv(
                'RAG_CONTEXT_SCORE_MARGIN',
                getattr(settings, 'RAG_CONTEXT_SCORE_MARGIN', 0.18),
            )
        )
        self.min_arabic_answer_ratio = float(
            os.getenv(
                'RAG_MIN_ARABIC_ANSWER_RATIO',
                getattr(settings, 'RAG_MIN_ARABIC_ANSWER_RATIO', 0.72),
            )
        )
        self.enable_arabic_rewrite = os.getenv(
            'RAG_ENABLE_ARABIC_REWRITE',
            str(getattr(settings, 'RAG_ENABLE_ARABIC_REWRITE', False)),
        ).lower() == 'true'
        self.rewrite_max_tokens = max(
            48,
            int(
                os.getenv(
                    'RAG_REWRITE_MAX_TOKENS',
                    getattr(settings, 'RAG_REWRITE_MAX_TOKENS', min(self.answer_max_tokens, 96)),
                )
            ),
        )
        self.rewrite_timeout_seconds = max(
            6.0,
            float(
                os.getenv(
                    'RAG_REWRITE_TIMEOUT_SECONDS',
                    getattr(settings, 'RAG_REWRITE_TIMEOUT_SECONDS', 20),
                )
            ),
        )
        self.max_primary_seconds_before_skip_rewrite = max(
            8.0,
            float(
                os.getenv(
                    'RAG_MAX_PRIMARY_SECONDS_BEFORE_SKIP_REWRITE',
                    getattr(settings, 'RAG_MAX_PRIMARY_SECONDS_BEFORE_SKIP_REWRITE', 25),
                )
            ),
        )
        self.enable_fallback_arabic_rewrite = os.getenv(
            'RAG_ENABLE_FALLBACK_ARABIC_REWRITE',
            str(getattr(settings, 'RAG_ENABLE_FALLBACK_ARABIC_REWRITE', True)),
        ).lower() == 'true'
        self.enable_fallback_query_language_rewrite = os.getenv(
            'RAG_ENABLE_FALLBACK_QUERY_LANGUAGE_REWRITE',
            str(getattr(settings, 'RAG_ENABLE_FALLBACK_QUERY_LANGUAGE_REWRITE', True)),
        ).lower() == 'true'
        self.fallback_rewrite_max_tokens = max(
            48,
            int(
                os.getenv(
                    'RAG_FALLBACK_REWRITE_MAX_TOKENS',
                    getattr(settings, 'RAG_FALLBACK_REWRITE_MAX_TOKENS', 90),
                )
            ),
        )
        self.fallback_rewrite_timeout_seconds = max(
            6.0,
            float(
                os.getenv(
                    'RAG_FALLBACK_REWRITE_TIMEOUT_SECONDS',
                    getattr(settings, 'RAG_FALLBACK_REWRITE_TIMEOUT_SECONDS', 12),
                )
            ),
        )

        self.include_summaries_in_query = os.getenv(
            'RAG_INCLUDE_SUMMARIES_IN_QUERY',
            str(getattr(settings, 'RAG_INCLUDE_SUMMARIES_IN_QUERY', False)),
        ).lower() == 'true'

        self.enable_agentic_rag = os.getenv(
            'RAG_ENABLE_AGENTIC_RAG',
            str(getattr(settings, 'RAG_ENABLE_AGENTIC_RAG', True)),
        ).lower() == 'true'
        self.enable_agentic_query_rewrite = os.getenv(
            'RAG_ENABLE_AGENTIC_QUERY_REWRITE',
            str(getattr(settings, 'RAG_ENABLE_AGENTIC_QUERY_REWRITE', True)),
        ).lower() == 'true'
        self.enable_cross_language_query_hint = os.getenv(
            'RAG_ENABLE_CROSS_LANGUAGE_QUERY_HINT',
            str(getattr(settings, 'RAG_ENABLE_CROSS_LANGUAGE_QUERY_HINT', True)),
        ).lower() == 'true'
        self.enable_agentic_self_check = os.getenv(
            'RAG_ENABLE_AGENTIC_SELF_CHECK',
            str(getattr(settings, 'RAG_ENABLE_AGENTIC_SELF_CHECK', True)),
        ).lower() == 'true'
        self.agentic_max_retrieval_attempts = max(
            1,
            int(
                os.getenv(
                    'RAG_AGENTIC_MAX_RETRIEVAL_ATTEMPTS',
                    getattr(settings, 'RAG_AGENTIC_MAX_RETRIEVAL_ATTEMPTS', 2),
                )
            ),
        )
        self.agentic_rewrite_max_tokens = max(
            16,
            int(
                os.getenv(
                    'RAG_AGENTIC_REWRITE_MAX_TOKENS',
                    getattr(settings, 'RAG_AGENTIC_REWRITE_MAX_TOKENS', 48),
                )
            ),
        )
        self.agentic_rewrite_timeout_seconds = max(
            4.0,
            float(
                os.getenv(
                    'RAG_AGENTIC_REWRITE_TIMEOUT_SECONDS',
                    getattr(settings, 'RAG_AGENTIC_REWRITE_TIMEOUT_SECONDS', 10),
                )
            ),
        )
        self.cross_language_hint_max_tokens = max(
            12,
            int(
                os.getenv(
                    'RAG_CROSS_LANGUAGE_HINT_MAX_TOKENS',
                    getattr(settings, 'RAG_CROSS_LANGUAGE_HINT_MAX_TOKENS', 24),
                )
            ),
        )
        self.cross_language_hint_timeout_seconds = max(
            3.0,
            float(
                os.getenv(
                    'RAG_CROSS_LANGUAGE_HINT_TIMEOUT_SECONDS',
                    getattr(settings, 'RAG_CROSS_LANGUAGE_HINT_TIMEOUT_SECONDS', 7),
                )
            ),
        )
        self.agentic_self_check_max_tokens = max(
            24,
            int(
                os.getenv(
                    'RAG_AGENTIC_SELF_CHECK_MAX_TOKENS',
                    getattr(settings, 'RAG_AGENTIC_SELF_CHECK_MAX_TOKENS', 72),
                )
            ),
        )
        self.agentic_self_check_timeout_seconds = max(
            4.0,
            float(
                os.getenv(
                    'RAG_AGENTIC_SELF_CHECK_TIMEOUT_SECONDS',
                    getattr(settings, 'RAG_AGENTIC_SELF_CHECK_TIMEOUT_SECONDS', 12),
                )
            ),
        )
        self.agentic_min_chunks = max(
            1,
            int(
                os.getenv(
                    'RAG_AGENTIC_MIN_CHUNKS',
                    getattr(settings, 'RAG_AGENTIC_MIN_CHUNKS', 1),
                )
            ),
        )
        self.agentic_min_top_score = float(
            os.getenv(
                'RAG_AGENTIC_MIN_TOP_SCORE',
                getattr(settings, 'RAG_AGENTIC_MIN_TOP_SCORE', 0.50),
            )
        )
        self.agentic_min_overlap = float(
            os.getenv(
                'RAG_AGENTIC_MIN_OVERLAP',
                getattr(settings, 'RAG_AGENTIC_MIN_OVERLAP', 0.05),
            )
        )
        self.agentic_min_chunks_pricing = max(
            1,
            int(
                os.getenv(
                    'RAG_AGENTIC_MIN_CHUNKS_PRICING',
                    getattr(settings, 'RAG_AGENTIC_MIN_CHUNKS_PRICING', max(2, self.agentic_min_chunks)),
                )
            ),
        )
        self.agentic_min_chunks_features = max(
            1,
            int(
                os.getenv(
                    'RAG_AGENTIC_MIN_CHUNKS_FEATURES',
                    getattr(settings, 'RAG_AGENTIC_MIN_CHUNKS_FEATURES', self.agentic_min_chunks),
                )
            ),
        )
        self.agentic_min_chunks_support = max(
            1,
            int(
                os.getenv(
                    'RAG_AGENTIC_MIN_CHUNKS_SUPPORT',
                    getattr(settings, 'RAG_AGENTIC_MIN_CHUNKS_SUPPORT', self.agentic_min_chunks),
                )
            ),
        )
        self.agentic_min_top_score_pricing = float(
            os.getenv(
                'RAG_AGENTIC_MIN_TOP_SCORE_PRICING',
                getattr(settings, 'RAG_AGENTIC_MIN_TOP_SCORE_PRICING', max(0.58, self.agentic_min_top_score)),
            )
        )
        self.agentic_min_top_score_features = float(
            os.getenv(
                'RAG_AGENTIC_MIN_TOP_SCORE_FEATURES',
                getattr(settings, 'RAG_AGENTIC_MIN_TOP_SCORE_FEATURES', max(0.48, self.agentic_min_top_score - 0.02)),
            )
        )
        self.agentic_min_top_score_support = float(
            os.getenv(
                'RAG_AGENTIC_MIN_TOP_SCORE_SUPPORT',
                getattr(settings, 'RAG_AGENTIC_MIN_TOP_SCORE_SUPPORT', max(0.55, self.agentic_min_top_score)),
            )
        )
        self.agentic_min_overlap_pricing = float(
            os.getenv(
                'RAG_AGENTIC_MIN_OVERLAP_PRICING',
                getattr(settings, 'RAG_AGENTIC_MIN_OVERLAP_PRICING', max(0.08, self.agentic_min_overlap)),
            )
        )
        self.agentic_min_overlap_features = float(
            os.getenv(
                'RAG_AGENTIC_MIN_OVERLAP_FEATURES',
                getattr(settings, 'RAG_AGENTIC_MIN_OVERLAP_FEATURES', max(0.04, self.agentic_min_overlap - 0.01)),
            )
        )
        self.agentic_min_overlap_support = float(
            os.getenv(
                'RAG_AGENTIC_MIN_OVERLAP_SUPPORT',
                getattr(settings, 'RAG_AGENTIC_MIN_OVERLAP_SUPPORT', max(0.07, self.agentic_min_overlap)),
            )
        )
        self.enable_lexical_grounding_check = os.getenv(
            'RAG_ENABLE_LEXICAL_GROUNDING_CHECK',
            str(getattr(settings, 'RAG_ENABLE_LEXICAL_GROUNDING_CHECK', True)),
        ).lower() == 'true'
        self.min_answer_context_coverage = float(
            os.getenv(
                'RAG_MIN_ANSWER_CONTEXT_COVERAGE',
                getattr(settings, 'RAG_MIN_ANSWER_CONTEXT_COVERAGE', 0.36),
            )
        )
        self.min_answer_context_coverage_strict = float(
            os.getenv(
                'RAG_MIN_ANSWER_CONTEXT_COVERAGE_STRICT',
                getattr(settings, 'RAG_MIN_ANSWER_CONTEXT_COVERAGE_STRICT', 0.44),
            )
        )

        self._summary_cache: Dict[str, Dict[str, Any]] = {}
        self._summary_cache_lock = threading.Lock()

        if not OLLAMA_AVAILABLE:
            logger.warning('Ollama not available.')
            self.llm_client = None
            self.model = None
            self.model_arabic = None
            return

        try:
            ollama_host = os.getenv('OLLAMA_BASE_URL', getattr(settings, 'OLLAMA_BASE_URL', 'http://ollama:11434'))
            request_timeout = float(os.getenv('OLLAMA_REQUEST_TIMEOUT_SECONDS', getattr(settings, 'OLLAMA_REQUEST_TIMEOUT_SECONDS', 90)))

            try:
                self.llm_client = ollama.Client(host=ollama_host, timeout=request_timeout)
            except TypeError:
                self.llm_client = ollama.Client(host=ollama_host)

            self.model = os.getenv('OLLAMA_MODEL', getattr(settings, 'OLLAMA_MODEL', 'llama3:latest'))
            self.model_arabic = os.getenv('OLLAMA_MODEL_ARABIC', getattr(settings, 'OLLAMA_MODEL_ARABIC', self.model))
        except Exception as exc:
            logger.error('Failed to initialize Ollama client: %s', exc)
            self.llm_client = None
            self.model = None
            self.model_arabic = None

    def _normalize_query_for_cache(self, query: str) -> str:
        return normalize_for_search(query)

    def _cache_key(self, query: str) -> str:
        return hashlib.md5(self._normalize_query_for_cache(query).encode("utf-8")).hexdigest()

    def _result_cache_key(self, query: str) -> str:
        return f"rag:result:{RESULT_CACHE_VERSION}:{self.tenant.id}:{self._cache_key(query)}"

    def _summary_cache_key(self, level: str, category: str) -> str:
        return f"rag:summary:{self.tenant.id}:{level}:{category}"

    def _is_arabic(self, text: str) -> bool:
        if not text:
            return False
        value = str(text)

        # Some clients can mangle Arabic into repeated "?" characters (encoding mismatch).
        # Treat this specific pattern as Arabic-intended input to avoid wrong-language answers.
        if CORRUPTED_ARABIC_QUERY_RE.match(value):
            return True

        arabic_chars = sum(1 for c in value if "\u0600" <= c <= "\u06ff")
        if arabic_chars == 0:
            return False

        latin_chars = sum(1 for c in value if ("a" <= c.lower() <= "z"))
        alpha_total = arabic_chars + latin_chars
        if alpha_total == 0:
            return False

        arabic_ratio = arabic_chars / alpha_total
        if arabic_ratio >= 0.20:
            return True

        arabic_tokens = re.findall(r"[\u0600-\u06FF]+", value)
        latin_tokens = re.findall(r"[A-Za-z]+", value)
        return bool(arabic_tokens) and len(arabic_tokens) >= len(latin_tokens)

    def _arabic_ratio(self, text: str) -> float:
        if not text:
            return 0.0
        ar = sum(1 for c in text if "\u0600" <= c <= "\u06ff")
        letters = sum(1 for c in text if c.isalpha())
        if letters == 0:
            return 0.0
        return ar / letters

    def _is_definition_question(self, query: str) -> bool:
        return bool(DEFINITION_QUERY_RE.search(query or ""))

    def _query_expects_multi_point(self, query: str) -> bool:
        return bool(MULTI_POINT_QUERY_RE.search(query or ""))

    def _query_asks_limitations(self, query: str) -> bool:
        return bool(LIMITATION_QUERY_RE.search(query or ""))

    def _query_focus(self, query: str) -> str:
        value = normalize_user_query(query)
        if WHY_QUERY_RE.search(value):
            return "reason"
        if self._is_definition_question(value):
            return "definition"
        if WHEN_QUERY_RE.search(value):
            return "time"
        if WHO_QUERY_RE.search(value):
            return "person"
        if WHERE_QUERY_RE.search(value):
            return "location"
        if QUANTITY_QUERY_RE.search(value):
            return "quantity"
        if HOW_QUERY_RE.search(value):
            return "procedure"
        if CAPABILITY_QUERY_RE.search(value):
            return "capability"
        if WHICH_QUERY_RE.search(value):
            return "choice"
        if self._query_expects_multi_point(value):
            return "reason"
        return "general"

    def _focus_signal_score(self, focus: str, text: str) -> float:
        value = normalize_document_text(text)
        if not value:
            return 0.0

        score = 0.0
        if focus == "reason":
            if POSITIVE_SECTION_HINT_RE.search(value):
                score += 0.12
            if ACTION_SENTENCE_RE.search(value):
                score += 0.08
        elif focus == "definition":
            score += self._definition_signal_score(value) + 0.03
        elif focus == "procedure":
            if PROCEDURAL_TEXT_HINT_RE.search(value):
                score += 0.16
            if PROCEDURAL_STEP_HINT_RE.search(value):
                score += 0.08
            if not (PROCEDURAL_TEXT_HINT_RE.search(value) or PROCEDURAL_STEP_HINT_RE.search(value)):
                if POSITIVE_SECTION_HINT_RE.search(value):
                    score -= 0.12
            if DEFINITION_TEXT_HINT_RE.search(value):
                score -= 0.04
        elif focus == "time":
            if TEMPORAL_TEXT_HINT_RE.search(value):
                score += 0.20
        elif focus == "person":
            if PERSON_TEXT_HINT_RE.search(value):
                score += 0.20
        elif focus == "location":
            if LOCATION_TEXT_HINT_RE.search(value):
                score += 0.20
        elif focus == "quantity":
            if QUANTITY_TEXT_HINT_RE.search(value):
                score += 0.16
        elif focus == "capability":
            if CAPABILITY_TEXT_HINT_RE.search(value):
                score += 0.16
        elif focus == "choice":
            if CHOICE_TEXT_HINT_RE.search(value):
                score += 0.14

        return score

    def _answer_matches_focus(self, focus: str, text: str) -> bool:
        value = normalize_document_text(text)
        if not value:
            return False
        if focus in {"general", "reason", "choice"}:
            return True
        if focus == "definition":
            return bool(DEFINITION_TEXT_HINT_RE.search(value))
        if focus == "procedure":
            return bool(PROCEDURAL_TEXT_HINT_RE.search(value) or PROCEDURAL_STEP_HINT_RE.search(value))
        if focus == "time":
            return bool(TEMPORAL_TEXT_HINT_RE.search(value))
        if focus == "person":
            return bool(PERSON_TEXT_HINT_RE.search(value))
        if focus == "location":
            return bool(LOCATION_TEXT_HINT_RE.search(value))
        if focus == "quantity":
            return bool(QUANTITY_TEXT_HINT_RE.search(value))
        if focus == "capability":
            return bool(CAPABILITY_TEXT_HINT_RE.search(value))
        return True

    def _answer_point_count(self, text: str) -> int:
        value = re.sub(r"\s+", " ", (text or "")).strip()
        if not value:
            return 0
        separators = value.count("\u2022") + value.count("- ") + value.count("\u061b") + value.count(";")
        sentence_like = len([p for p in re.split(r"[\.!\?\u061F\u061B;]+", value) if p.strip()])
        return max(separators, sentence_like)

    def _definition_signal_score(self, text: str) -> float:
        if not text:
            return 0.0
        score = 0.0
        if DEFINITION_TEXT_HINT_RE.search(text):
            score += 0.08
        if PROCEDURAL_TEXT_HINT_RE.search(text):
            score -= 0.08
        return score

    def _split_sentences(self, text: str) -> List[str]:
        value = re.sub(r"\s+", " ", (text or "")).strip()
        if not value:
            return []
        parts = [part.strip() for part in SENTENCE_SPLIT_RE.split(value) if part.strip()]
        return parts if parts else [value]

    def _is_heading_like_sentence(self, text: str) -> bool:
        value = re.sub(r"\s+", " ", (text or "")).strip()
        if not value:
            return True
        if NOISY_OCR_LINE_RE.search(value) and len(value) < 120:
            return True
        if HEADING_UPPER_RE.search(value):
            return True
        if HEADING_TITLE_RE.search(value):
            return True
        if HEADING_PHRASE_RE.search(value) and len(value) < 140 and not re.search(r"[.;:,\u061B\u060C]", value):
            return True
        tokens = [tok for tok in re.findall(r"[A-Za-z]+", value) if tok]
        if tokens and len(tokens) <= 8:
            upper_tokens = sum(1 for tok in tokens if tok.isupper())
            if (upper_tokens / len(tokens)) >= 0.45:
                return True
        if value.endswith("?") and len(tokens) <= 10:
            return True
        return False

    def _compact_point_line(self, text: str, *, max_words: int = 16, max_chars: int = 120) -> str:
        value = normalize_document_text(text)
        value = re.sub(r"^\s*(?:[-\u2022\u25CF\u25AA]|\d{1,2}[\)\.\-])\s*", "", value)
        value = re.sub(r"^[^\w\u0600-\u06FF]+", "", value)
        value = re.sub(r"\s+", " ", value).strip(" -:;,.")
        if not value:
            return ""

        parts = re.split(r"(?<=[\.:;\u061B\u060C])\s+|\s+[-\u2013\u2014]\s+", value)
        candidate = parts[0].strip(" -:;,.") if parts else value
        if len(candidate) < 12:
            candidate = value

        words = candidate.split()
        if len(words) > max_words:
            candidate = " ".join(words[:max_words]).strip(" -:;,.")
        if len(candidate) > max_chars:
            candidate = candidate[:max_chars].rsplit(" ", 1)[0].strip(" -:;,.")
        return candidate

    def _build_arabic_extractive_response(self, snippet: str, *, source_text: str = "", query: str = "") -> str:
        value = normalize_document_text(snippet)
        value = re.sub(r"^[A-Z][A-Z\s\-:&/]{4,}\s+", "", value).strip()
        value = re.sub(r"\s+", " ", value).strip(" -:;,.")
        if not value:
            return ""

        if self._arabic_ratio(value) >= 0.20:
            compact = value
            if len(compact) > 300:
                compact = compact[:300].rsplit(" ", 1)[0].strip() + "..."
            return compact

        # If extractive text is mostly non-Arabic, try a generic rewrite to Arabic
        # without adding domain-specific assumptions.
        rewritten = self._rewrite_fallback_in_arabic(query or value, value)
        rewritten = normalize_document_text(rewritten)
        rewritten = re.sub(r"\s+", " ", rewritten).strip(" -:;,.")
        if rewritten and self._arabic_ratio(rewritten) >= 0.12:
            return rewritten[:320] if len(rewritten) <= 320 else rewritten[:320].rsplit(" ", 1)[0].strip() + "..."

        compact = value[:300] if len(value) <= 300 else value[:300].rsplit(" ", 1)[0].strip() + "..."
        return compact

    def _rule_based_arabic_render(self, text: str) -> str:
        value = normalize_document_text(text)
        if not value:
            return ""
        if re.match(r"^\s*(?:CREATE|GRANT|ALTER|DROP|INSERT|UPDATE|DELETE|SELECT)\b", value, flags=re.IGNORECASE):
            return re.sub(r"\s+", " ", value).strip()
        replacements = [
            (r"\bsql\s+scripts?\b", "سكريبتات SQL"),
            (r"\bcreation of tablespaces\b", "إنشاء مساحات الجداول"),
            (r"\bcreation of profiles\b", "إنشاء ملفات التعريف"),
            (r"\bcreation of roles\b", "إنشاء الأدوار"),
            (r"\bcreation of users\b", "إنشاء المستخدمين"),
            (r"\bcreation of privileges\b", "إنشاء الصلاحيات"),
            (r"\bcreation of profiles\b", "إنشاء ملفات التعريف"),
            (r"\bpolicies enforced\b", "سياسات مُطبقة"),
            (r"\bdepartment has isolated access\b", "القسم يمتلك وصولًا معزولًا"),
            (r"\bstrict security policies\b", "سياسات أمان صارمة"),
            (r"\bwith roles and profiles\b", "مع الأدوار وملفات التعريف"),
            (r"\benforcing\b", "تفرض"),
            (r"\broles\b", "الأدوار"),
            (r"\bprofiles\b", "ملفات التعريف"),
            (r"\bprofile\b", "ملف التعريف"),
            (r"\bpolicy\b", "سياسة"),
            (r"\bpolicies\b", "سياسات"),
            (r"\bincreases?\b", "\u064a\u0632\u064a\u062f"),
            (r"\breduces?\b", "\u064a\u0642\u0644\u0644"),
            (r"\bsaves?\b", "\u064a\u0648\u0641\u0631"),
            (r"\benables?\b", "\u064a\u062a\u064a\u062d"),
            (r"\bimproves?\b", "\u064a\u062d\u0633\u0646"),
            (r"\bsupports?\b", "\u064a\u062f\u0639\u0645"),
            (r"\bautomation\b", "\u0627\u0644\u0623\u062a\u0645\u062a\u0629"),
            (r"\btesting\b", "\u0627\u0644\u0627\u062e\u062a\u0628\u0627\u0631"),
            (r"\berrors?\b", "\u0627\u0644\u0623\u062e\u0637\u0627\u0621"),
            (r"\bspeed\b", "\u0627\u0644\u0633\u0631\u0639\u0629"),
            (r"\befficiency\b", "\u0627\u0644\u0643\u0641\u0627\u0621\u0629"),
            (r"\btime\b", "\u0627\u0644\u0648\u0642\u062a"),
            (r"\bcost\b", "\u0627\u0644\u062a\u0643\u0644\u0641\u0629"),
            (r"\bcoverage\b", "\u0627\u0644\u062a\u063a\u0637\u064a\u0629"),
            (r"\bcontinuous\b", "\u0627\u0644\u0645\u0633\u062a\u0645\u0631\u0629"),
            (r"\btools?\b", "\u0627\u0644\u0623\u062f\u0648\u0627\u062a"),
        ]
        for pattern, replacement in replacements:
            value = re.sub(pattern, replacement, value, flags=re.IGNORECASE)
        value = re.sub(r"\s+", " ", value).strip(" -:;,.")
        return value

    def _collect_fallback_sentences(self, context: str) -> List[str]:
        blocks = [block.strip() for block in (context or '').split('\n\n---\n\n') if block.strip()]
        sentences: List[str] = []
        for block in blocks:
            lines = [line.strip() for line in block.splitlines() if line.strip()]
            body_lines = lines[1:] if (lines and lines[0].startswith('[Evidence')) else lines
            if not body_lines:
                continue

            # Keep original line boundaries first (important for OCR/bulleted PDFs).
            for line in body_lines:
                sentence = re.sub(r"\s+", " ", line).strip(" -:;,.")
                if len(sentence) < 14:
                    continue
                if self._is_heading_like_sentence(sentence):
                    continue
                if CONTINUATION_LINE_RE.search(sentence):
                    continue
                if sentence.endswith(","):
                    continue
                if sentence.count(";") >= 2 and not ACTION_SENTENCE_RE.search(sentence):
                    continue
                sentences.append(sentence)

            # Also add sentence-split candidates from merged text for prose paragraphs.
            candidate_text = " ".join(body_lines).strip()
            for sentence in self._split_sentences(candidate_text):
                sentence = re.sub(r"\s+", " ", sentence).strip(" -:;,.")
                if len(sentence) < 18:
                    continue
                if self._is_heading_like_sentence(sentence):
                    continue
                sentences.append(sentence)
        return sentences

    def _extract_structured_points(self, query: str, context: str, limit: int = 6) -> List[str]:
        blocks = [block.strip() for block in (context or '').split('\n\n---\n\n') if block.strip()]
        q_tokens = self._expanded_query_tokens(query)
        focus = self._query_focus(query)
        multi_point_query = self._query_expects_multi_point(query)
        limitations_query = self._query_asks_limitations(query)
        action_points: List[str] = []
        title_points: List[str] = []
        seen_keys: Set[str] = set()

        for block in blocks:
            lines = [line.strip() for line in block.splitlines() if line.strip()]
            body_lines = lines[1:] if (lines and lines[0].startswith('[Evidence')) else lines
            for raw_line in body_lines:
                line = re.sub(r"\s+", " ", raw_line).strip(" -:;,.")
                line = re.sub(r"^\s*(?:[-\u2022\u25CF\u25AA]|\d{1,2}[\)\.\-])\s*", "", line)
                line = re.sub(r"^[^\w\u0600-\u06FF]+", "", line).strip(" -:;,.")
                if len(line) < 10:
                    continue
                if CONTINUATION_LINE_RE.search(line):
                    continue
                if line.endswith(","):
                    continue
                if len(line) > 220 and not ACTION_SENTENCE_RE.search(line):
                    continue
                if re.fullmatch(r"[A-Z0-9\s\-_/]{4,}", line):
                    continue
                if self._is_heading_like_sentence(line):
                    continue
                if not limitations_query and NEGATIVE_SECTION_HINT_RE.search(line):
                    continue

                word_count = len(re.findall(r"[A-Za-z0-9]+|[\u0600-\u06FF]+", line))
                is_short_title = word_count <= 14 and not re.search(r"[\.!\?:;,\u061B\u060C]", line)
                has_action = bool(STARTS_WITH_ACTION_RE.search(line) or ACTION_SENTENCE_RE.search(line))
                has_positive = bool(POSITIVE_SECTION_HINT_RE.search(line))
                s_tokens = set(self._tokenize(line))
                overlap = (len(q_tokens.intersection(s_tokens)) / len(q_tokens)) if q_tokens else 0.0

                if not self._is_arabic(query):
                    if re.match(r"^[a-z]", line) and not STARTS_WITH_ACTION_RE.search(line):
                        continue

                if multi_point_query and not limitations_query and not (has_action or has_positive):
                    continue
                if is_short_title and not has_action and overlap < 0.12:
                    continue
                if not (is_short_title or has_action):
                    continue

                compact = self._compact_point_line(line)
                if len(compact) < 10:
                    continue
                key = normalize_for_search(compact)
                if not key or key in seen_keys:
                    continue
                seen_keys.add(key)
                if has_action:
                    action_points.append(compact)
                elif is_short_title:
                    title_points.append(compact)

                if (len(action_points) + len(title_points)) >= max(1, limit):
                    break
            if (len(action_points) + len(title_points)) >= max(1, limit):
                break

        if len(action_points) >= 3:
            ordered = action_points
        else:
            ordered = action_points + title_points
        return ordered[: max(1, limit)]

    def _pick_supporting_fallback_sentences(self, query: str, context: str, limit: int = 3) -> List[str]:
        candidates = self._collect_fallback_sentences(context)
        if not candidates:
            return []

        q_tokens = self._expanded_query_tokens(query)
        focus = self._query_focus(query)
        multi_point_query = self._query_expects_multi_point(query)
        limitations_query = self._query_asks_limitations(query)
        scored: List[Tuple[float, str]] = []

        for sentence in candidates:
            if multi_point_query and not limitations_query and NEGATIVE_SECTION_HINT_RE.search(sentence):
                continue
            s_tokens = set(self._tokenize(sentence))
            overlap = (len(q_tokens.intersection(s_tokens)) / len(q_tokens)) if q_tokens else 0.0
            score = overlap
            score += self._focus_signal_score(focus, sentence)

            if re.search(r"^\s*(?:[-\u2022]|\d{1,2}[\)\.\-])\s*", sentence):
                score += 0.06
            if ACTION_SENTENCE_RE.search(sentence):
                score += 0.08
            if STARTS_WITH_ACTION_RE.search(sentence):
                score += 0.12
            if multi_point_query and POSITIVE_SECTION_HINT_RE.search(sentence):
                score += 0.08
            if len(sentence) > 340:
                score -= 0.05

            scored.append((score, sentence))

        scored.sort(key=lambda row: row[0], reverse=True)
        selected: List[str] = []
        seen_keys = set()
        for score, sentence in scored:
            has_signal = bool(
                ACTION_SENTENCE_RE.search(sentence)
                or STARTS_WITH_ACTION_RE.search(sentence)
                or POSITIVE_SECTION_HINT_RE.search(sentence)
            )
            if multi_point_query and not limitations_query and not has_signal:
                continue
            if not self._is_arabic(query):
                if re.match(r"^[a-z]", sentence) and not STARTS_WITH_ACTION_RE.search(sentence):
                    continue
            if focus == "procedure" and not (PROCEDURAL_TEXT_HINT_RE.search(sentence) or PROCEDURAL_STEP_HINT_RE.search(sentence)):
                if score < 0.16:
                    continue
            if focus == "time" and not TEMPORAL_TEXT_HINT_RE.search(sentence):
                if score < 0.14:
                    continue
            if focus == "person" and not PERSON_TEXT_HINT_RE.search(sentence):
                if score < 0.14:
                    continue
            if focus == "location" and not LOCATION_TEXT_HINT_RE.search(sentence):
                if score < 0.14:
                    continue
            if focus == "quantity" and not QUANTITY_TEXT_HINT_RE.search(sentence):
                if score < 0.14:
                    continue
            if focus == "capability" and not CAPABILITY_TEXT_HINT_RE.search(sentence):
                if score < 0.14:
                    continue
            if focus == "choice" and not CHOICE_TEXT_HINT_RE.search(sentence):
                if score < 0.14:
                    continue
            if CONTINUATION_LINE_RE.search(sentence):
                continue
            if multi_point_query:
                if score < 0.01 and selected and not has_signal:
                    continue
            else:
                if score < 0.01 and selected:
                    continue
            candidate = self._compact_point_line(sentence) if multi_point_query else sentence
            key = normalize_for_search(candidate)
            if not key or key in seen_keys:
                continue
            seen_keys.add(key)
            selected.append(candidate)
            if len(selected) >= max(1, limit):
                break

        if multi_point_query and selected:
            starts_with_action = [s for s in selected if STARTS_WITH_ACTION_RE.search(s)]
            if len(starts_with_action) >= 2:
                rest = [s for s in selected if s not in starts_with_action]
                selected = (starts_with_action + rest)[: max(1, limit)]

        return selected

    def _extract_topic_from_query(self, query: str) -> str:
        value = normalize_user_query(query)
        for pattern in TOPIC_CAPTURE_PATTERNS:
            match = pattern.search(value)
            if match:
                topic = match.group(1).strip(" \t\n\r:;,.!?\u061f\u060c")
                if topic:
                    return topic
        return value.strip(" \t\n\r:;,.!?\u061f\u060c")

    def _pick_best_fallback_snippet(self, query: str, context: str) -> str:
        supporting = self._pick_supporting_fallback_sentences(query, context, limit=1)
        if supporting:
            return supporting[0]

        blocks = [block.strip() for block in (context or '').split('\n\n---\n\n') if block.strip()]
        if not blocks:
            return ""

        q_tokens = self._expanded_query_tokens(query)
        definition_query = self._is_definition_question(query)
        focus = self._query_focus(query)
        best_text = ""
        best_score = -1.0

        for block in blocks:
            lines = [line.strip() for line in block.splitlines() if line.strip()]
            if lines and lines[0].startswith('[Evidence'):
                candidate_text = " ".join(lines[1:]).strip()
            else:
                candidate_text = " ".join(lines).strip()

            if not candidate_text:
                continue

            for sentence in self._split_sentences(candidate_text):
                if len(sentence) < 24:
                    continue

                s_tokens = set(self._tokenize(sentence))
                overlap = (len(q_tokens.intersection(s_tokens)) / len(q_tokens)) if q_tokens else 0.0

                score = overlap
                if definition_query:
                    score += self._definition_signal_score(sentence)
                else:
                    score += 0.03 if not PROCEDURAL_TEXT_HINT_RE.search(sentence) else 0.0
                score += self._focus_signal_score(focus, sentence)

                if focus == "definition":
                    if "?" in sentence[:80]:
                        score -= 0.12
                    if PERSON_TEXT_HINT_RE.search(sentence) or TEMPORAL_TEXT_HINT_RE.search(sentence):
                        score -= 0.10
                    if not DEFINITION_TEXT_HINT_RE.search(sentence):
                        score -= 0.05
                elif focus == "procedure":
                    if not (PROCEDURAL_TEXT_HINT_RE.search(sentence) or PROCEDURAL_STEP_HINT_RE.search(sentence)):
                        score -= 0.08

                if len(sentence) > 320:
                    score -= 0.05
                if self._is_heading_like_sentence(sentence):
                    score -= 0.22

                if score > best_score:
                    best_score = score
                    best_text = sentence

        if not best_text:
            for block in blocks:
                lines = [line.strip() for line in block.splitlines() if line.strip()]
                if lines and lines[0].startswith('[Evidence'):
                    best_text = " ".join(lines[1:]).strip()
                else:
                    best_text = " ".join(lines).strip()
                if best_text:
                    break

        best_text = re.sub(r"\s+", " ", best_text).strip()
        if len(best_text) > 320:
            best_text = best_text[:320].rsplit(' ', 1)[0].strip() + '...'
        return best_text

    def _extract_focus_atomic_answer(self, query: str, context: str) -> str:
        focus = self._query_focus(query)
        text = normalize_document_text(context or "")
        if not text:
            return ""

        if focus == "person":
            patterns = [
                r"\bPresented by:\s*([^\n,|]{2,80})",
                r"\bAuthor:\s*([^\n,|]{2,80})",
                r"(?:^|\s)\u0625\u0639\u062f\u0627\u062f[:\s]*([^\n,|]{2,80})",
                r"(?:^|\s)\u0628\u0648\u0627\u0633\u0637\u0629[:\s]*([^\n,|]{2,80})",
            ]
            for pattern in patterns:
                match = re.search(pattern, text, flags=re.IGNORECASE)
                if match:
                    return re.sub(r"\s+", " ", match.group(1)).strip(" -:;,.")

        if focus == "time":
            match = re.search(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", text)
            if match:
                return match.group(0)
            match = re.search(
                r"(?:^|\s)(?:\u062a\u0627\u0631\u064a\u062e|date)[:\s]+([^\n,|]{3,40})",
                text,
                flags=re.IGNORECASE,
            )
            if match:
                return re.sub(r"\s+", " ", match.group(1)).strip(" -:;,.")

        if focus == "location":
            patterns = [
                r"\bUniversity:\s*([^\n,|]{2,120})",
                r"(?:^|\s)\u062c\u0627\u0645\u0639\u0629[:\s]*([^\n,|]{2,120})",
                r"\bLocation:\s*([^\n,|]{2,120})",
                r"(?:^|\s)\u0645\u0648\u0642\u0639[:\s]*([^\n,|]{2,120})",
            ]
            for pattern in patterns:
                match = re.search(pattern, text, flags=re.IGNORECASE)
                if match:
                    return re.sub(r"\s+", " ", match.group(1)).strip(" -:;,.")

        if focus == "quantity":
            match = re.search(r"\b\d+(?:\.\d+)?\s*(?:%|percent|usd|eur|\$)\b", text, flags=re.IGNORECASE)
            if match:
                return match.group(0)
            match = re.search(r"\b\d+(?:\.\d+)?\b", text)
            if match:
                return match.group(0)

        return ""

    def _rewrite_fallback_in_arabic(self, query: str, snippet: str) -> str:
        if not snippet:
            return snippet
        if not self.enable_fallback_arabic_rewrite or not self.llm_client:
            return snippet
        if not self._is_arabic(query):
            return snippet
        if self._arabic_ratio(snippet) >= 0.45:
            return snippet

        model_name = self._model_for_query(query)
        prompt = (
            "Rewrite the following answer into clear Arabic while preserving all facts and all points.\n"
            "If the input is a list or multi-line content, keep the same list structure and line order.\n"
            "Do not add facts.\n"
            "Keep technical/product names in English exactly as-is.\n"
            "Keep SQL commands exactly as-is.\n"
            "Remove weird symbols and extra spaces.\n"
            "Return Arabic answer text only.\n\n"
            f"Text:\n{snippet}\n\nArabic:"
        )
        try:
            rewritten = self._llm_generate(
                prompt,
                max_tokens=min(self.fallback_rewrite_max_tokens, self.answer_max_tokens),
                model_name=model_name,
                timeout_seconds=max(
                    min(self.fallback_rewrite_timeout_seconds, self.max_response_seconds),
                    45.0,
                ),
                num_ctx=min(self.llm_num_ctx, 1024),
                temperature=0.0,
                top_p=0.1,
            ).strip()
            rewritten = sanitize_generated_answer(query, rewritten)
            if PROMPT_LEAK_RE.search(rewritten):
                return snippet
            if rewritten and self._arabic_ratio(rewritten) >= 0.15:
                return rewritten
        except Exception as exc:
            logger.info('Fallback Arabic rewrite skipped: %s', exc)

        # Preserve informative content instead of incorrectly downgrading to NO_INFO.
        return snippet

    def _rewrite_fallback_to_query_language(self, query: str, snippet: str) -> str:
        if not snippet:
            return snippet
        if not self.enable_fallback_query_language_rewrite or not self.llm_client:
            return snippet
        if self._is_arabic(query):
            return snippet
        if self._arabic_ratio(snippet) <= 0.22:
            return snippet

        model_name = self._model_for_query(query)
        prompt = (
            "Rewrite the following answer in the same language as the user query.\n"
            "Do not add facts.\n"
            "Keep product names, technical terms, and acronyms exactly as-is.\n"
            "Remove odd symbols and extra spaces.\n"
            "Return answer text only.\n\n"
            f"User query:\n{query}\n\n"
            f"Answer:\n{snippet}\n\n"
            "Rewritten answer:"
        )
        try:
            rewritten = self._llm_generate(
                prompt,
                max_tokens=min(self.fallback_rewrite_max_tokens, self.answer_max_tokens),
                model_name=model_name,
                timeout_seconds=max(
                    min(self.fallback_rewrite_timeout_seconds, self.max_response_seconds),
                    45.0,
                ),
                num_ctx=min(self.llm_num_ctx, 1024),
                temperature=0.0,
                top_p=0.1,
            ).strip()
            rewritten = sanitize_generated_answer(query, rewritten)
            if PROMPT_LEAK_RE.search(rewritten):
                return snippet
            if rewritten:
                return rewritten
        except Exception as exc:
            logger.info('Fallback query-language rewrite skipped: %s', exc)

        return snippet

    def _force_arabic_render(self, text: str) -> str:
        value = normalize_document_text(text or "")
        if not value:
            return ""

        lines: List[str] = []
        for raw in value.splitlines():
            line = re.sub(r"\s+", " ", raw).strip()
            if not line:
                continue
            # Keep headings/product names as-is, translate explanatory text deterministically.
            rendered = self._rule_based_arabic_render(line)
            rendered = re.sub(r"\s+", " ", rendered).strip(" -:;,.")
            if rendered:
                lines.append(rendered)
        if not lines:
            return value
        return "\n".join(lines)

    def _ensure_query_language(self, query: str, answer: str, *, allow_llm_rewrite: bool = True) -> str:
        if not answer:
            return answer
        if self._is_arabic(query):
            if self._arabic_ratio(answer) >= 0.20:
                return answer
            q_tokens = self._expanded_query_tokens(query)
            technical_policy_query = any(
                tok in q_tokens
                for tok in {"sql", "script", "scripts", "create", "grant", "profile", "profiles", "policy", "policies", "privilege", "privileges"}
            )
            if self._is_structured_technical_answer(answer):
                forced = self._force_arabic_render(answer)
                if forced:
                    return forced
            candidate = answer
            if technical_policy_query:
                forced = self._force_arabic_render(answer)
                if forced:
                    return forced
            if allow_llm_rewrite and self.extractive_use_llm_rewrite and not technical_policy_query:
                rewritten = self._rewrite_fallback_in_arabic(query, answer)
                if rewritten:
                    candidate = rewritten
            if MIXED_SCRIPT_RE.search(candidate) or self._arabic_ratio(candidate) < 0.12:
                forced = self._force_arabic_render(answer)
                if forced and self._arabic_ratio(forced) >= 0.12:
                    return forced
                extractive_ar = self._build_arabic_extractive_response(answer, query=query)
                if extractive_ar:
                    return extractive_ar
            return candidate

        # Non-Arabic query path: enforce query language fallback when answer is mostly Arabic.
        if self._arabic_ratio(answer) <= 0.22:
            return answer
        rewritten = self._rewrite_fallback_to_query_language(query, answer)
        return rewritten or answer

    def _expanded_query_tokens(self, query: str) -> Set[str]:
        token_set = set(self._tokenize(query))
        normalized_query = normalize_for_search(query)
        if self._is_arabic(query):
            for pattern, expansions in AR_QUERY_EXPANSIONS:
                if pattern.search(normalized_query):
                    token_set.update(expansions)
        return token_set

    def _expand_query_for_retrieval(self, query: str) -> str:
        normalized_query = normalize_for_search(query)
        extras: List[str] = []
        focus = self._query_focus(query)
        if self._is_arabic(query):
            for pattern, expansions in AR_QUERY_EXPANSIONS:
                if pattern.search(normalized_query):
                    extras.extend(expansions)
        elif self._query_expects_multi_point(query):
            extras.extend(["benefits", "advantages", "reasons", "key points"])
        elif focus == "definition":
            extras.extend(["definition", "overview", "what is"])
        elif focus == "procedure":
            extras.extend(["steps", "how to", "guide", "setup"])
        elif focus == "time":
            extras.extend(["date", "timeline", "schedule", "when"])
        elif focus == "person":
            extras.extend(["author", "presented by", "who"])
        elif focus == "location":
            extras.extend(["location", "where", "address"])
        elif focus == "quantity":
            extras.extend(["number", "count", "price", "cost"])
        elif focus == "capability":
            extras.extend(["supports", "compatible", "availability"])
        elif focus == "choice":
            extras.extend(["options", "compare", "best choice"])
        if not extras:
            return normalize_for_search(query)
        # Place expanded English retrieval hints first so keyword search can match English source chunks.
        expanded = " ".join(sorted(set(extras)))
        return f"{expanded} {normalize_for_search(query)}".strip()

    def _tokenize(self, text: str) -> List[str]:
        normalized_text = normalize_for_search(text)
        tokens = []
        for raw in TOKEN_RE.findall(normalized_text):
            if len(raw) < 2:
                continue
            if raw in EN_STOPWORDS or raw in AR_STOPWORDS:
                continue
            tokens.append(raw)
        return tokens

    def _query_anchor_tokens(self, query: str) -> Set[str]:
        tokens = self._tokenize(query)
        anchors: List[str] = []
        for token in tokens:
            if len(token) < 4:
                continue
            if token in GENERIC_QUERY_TOKENS:
                continue
            anchors.append(token)
        if anchors:
            return set(anchors[:8])

        backup = [tok for tok in tokens if len(tok) >= 4 and tok not in GENERIC_QUERY_TOKENS]
        backup = sorted(set(backup), key=lambda t: len(t), reverse=True)
        return set(backup[:3])

    def _is_abstention_answer(self, answer: str) -> bool:
        value = (answer or "").strip()
        if not value:
            return True
        value_lower = re.sub(r"\s+", " ", value).strip().lower()
        if len(value_lower) < 5:
            return True
        value_compact = re.sub(r"\s+", "", value_lower)
        if any(
            (fragment.lower() in value_lower) or (re.sub(r"\s+", "", fragment.lower()) in value_compact)
            for fragment in ABSTENTION_SUBSTRINGS
        ):
            return True
        return any(pattern.search(value) for pattern in ABSTENTION_PATTERNS)

    def _no_info_message(self, question: str) -> str:
        if self._is_arabic(question):
            return "ما عندي علم بإجابة دقيقة من الوثائق المتاحة."
        return "I could not find a clear answer in the available documents."

    def _service_unavailable_message(self, question: str) -> str:
        if self._is_arabic(question):
            return "خدمة الذكاء الاصطناعي بطيئة أو غير متاحة حاليًا. حاول مجددًا بعد قليل."
        return "The AI service is currently slow or unavailable. Please try again shortly."

    def detect_intent(self, question: str) -> str:
        q_lower = question.lower()
        scores = {cat: 0 for cat in INTENT_KEYWORDS}
        for cat, keywords in INTENT_KEYWORDS.items():
            for kw in keywords:
                if kw in q_lower:
                    scores[cat] += 1

        best = max(scores, key=scores.get)
        return best if scores[best] > 0 else 'general'

    def retrieve(self, query: str, k: int | None = None) -> List[Dict]:
        k = k or self.retrieval_k
        semantic_k = max(k * 2, self.max_detail_chunks * (4 if self._query_expects_multi_point(query) else 3))
        semantic_query = normalize_user_query(query)
        lexical_query = self._expand_query_for_retrieval(query)
        focus = self._query_focus(query)

        try:
            semantic_results = self.vector_store.similarity_search(semantic_query, k=semantic_k)
        except Exception:
            semantic_results = []

        max_semantic = max((r.get('similarity_score', 0.0) for r in semantic_results), default=0.0)
        query_tokens = self._expanded_query_tokens(query)
        should_use_keyword = (
            self.enable_keyword_search
            and len(query_tokens) >= 2
            and (
                not semantic_results
                or max_semantic < self.keyword_fallback_threshold
                or self._is_arabic(query)
                or self._query_expects_multi_point(query)
                or focus in {"definition", "procedure", "time", "person", "location", "quantity", "capability", "choice"}
            )
        )

        keyword_results: List[Dict] = []
        if should_use_keyword:
            try:
                keyword_results = self.vector_store.keyword_search(lexical_query, k=max(k, semantic_k))
            except Exception:
                keyword_results = []

        merged: Dict[str, Dict[str, Any]] = {}
        normalized_query = normalize_for_search(query)

        def _ingest(rows: List[Dict], *, source_kind: str):
            for rank, row in enumerate(rows, start=1):
                content = normalize_document_text(row.get('content', ''))
                if not content:
                    continue
                key = normalize_for_search(content)
                if not key:
                    continue
                base = float(row.get('similarity_score', 0.0))
                rrf = 1.0 / (60.0 + rank)
                phrase_bonus = 0.08 if (normalized_query and normalized_query in key) else 0.0
                focus_bonus = min(0.16, max(0.0, self._focus_signal_score(focus, content)))
                hybrid = min(0.99, (base * 0.76) + (rrf * 8.0) + phrase_bonus + (focus_bonus * 0.45))

                existing = merged.get(key)
                if existing is None:
                    copied = dict(row)
                    copied['content'] = content
                    copied['similarity_score'] = max(base, hybrid)
                    copied['_hybrid_source'] = source_kind
                    merged[key] = copied
                    continue

                if hybrid > float(existing.get('similarity_score', 0.0)):
                    existing['similarity_score'] = hybrid
                    existing['_hybrid_source'] = source_kind

        _ingest(semantic_results, source_kind='semantic')
        _ingest(keyword_results, source_kind='keyword')
        unique = list(merged.values())
        unique.sort(key=lambda r: float(r.get('similarity_score', 0.0)), reverse=True)
        return unique[: max(k * 3, self.max_detail_chunks * 3)]

    def _document_key(self, chunk: Dict) -> str:
        metadata = chunk.get('metadata', {}) or {}
        return str(metadata.get('document_id') or metadata.get('source') or '__unknown__')

    def _apply_document_boost(self, chunks: List[Dict]) -> None:
        if not chunks:
            return

        grouped_scores: Dict[str, List[float]] = defaultdict(list)
        for chunk in chunks:
            grouped_scores[self._document_key(chunk)].append(float(chunk.get('final_score', 0.0)))

        document_scores: Dict[str, float] = {}
        for doc_key, scores in grouped_scores.items():
            scores = sorted(scores, reverse=True)
            top1 = scores[0]
            top2_avg = sum(scores[:2]) / min(2, len(scores))
            density_bonus = min(len(scores), 3) * self.document_density_bonus
            document_scores[doc_key] = (top1 * 0.74) + (top2_avg * 0.24) + density_bonus

        for chunk in chunks:
            doc_key = self._document_key(chunk)
            doc_score = document_scores.get(doc_key, 0.0)
            chunk['document_score'] = round(doc_score, 4)
            chunk['final_score'] = round(float(chunk.get('final_score', 0.0)) + (doc_score * self.document_boost_weight), 4)

    def _append_neighbor_chunks_for_definition(self, selected: List[Dict]) -> List[Dict]:
        if not selected:
            return selected
        top_meta = selected[0].get('metadata', {}) or {}
        document_id = top_meta.get('document_id')
        chunk_index = top_meta.get('chunk_index')
        if not document_id or chunk_index is None:
            return selected
        try:
            index_value = int(chunk_index)
        except (TypeError, ValueError):
            return selected

        try:
            from apps.documents.models import DocumentChunk
        except Exception:
            return selected

        neighbors = list(
            DocumentChunk.objects.filter(
                document_id=document_id,
                chunk_index__gte=max(0, index_value - 1),
                chunk_index__lte=index_value + 3,
            )
            .select_related("document")
            .order_by("chunk_index")
        )
        if not neighbors:
            return selected

        existing_keys = {normalize_for_search(str(c.get('content', ''))) for c in selected}
        expanded = list(selected)
        baseline_score = float(selected[0].get('final_score', 0.0))
        baseline_overlap = float(selected[0].get('lexical_overlap', 0.0))

        for row in neighbors:
            content = normalize_document_text(row.content or "")
            key = normalize_for_search(content)
            if not content or not key or key in existing_keys:
                continue
            existing_keys.add(key)
            metadata = dict(row.metadata or {})
            metadata.setdefault('document_id', str(row.document_id))
            metadata.setdefault('source', row.document.original_filename)
            metadata.setdefault('chunk_index', row.chunk_index)
            expanded.append(
                {
                    'content': content,
                    'metadata': metadata,
                    'similarity_score': max(0.0, baseline_score - 0.12),
                    'lexical_overlap': max(0.0, baseline_overlap - 0.08),
                    'anchor_overlap': max(0.0, float(selected[0].get('anchor_overlap', 0.0)) - 0.08),
                    'document_score': float(selected[0].get('document_score', 0.0)),
                    'final_score': max(0.0, baseline_score - 0.10),
                }
            )
            if len(expanded) >= max(self.max_detail_chunks, 6):
                break

        return expanded

    def _rank_documents(self, ranked_chunks: List[Dict]) -> List[Tuple[str, float]]:
        scores: Dict[str, float] = {}
        for chunk in ranked_chunks:
            doc_key = self._document_key(chunk)
            score = float(chunk.get('document_score', chunk.get('final_score', 0.0)))
            if score > scores.get(doc_key, -1.0):
                scores[doc_key] = score
        return sorted(scores.items(), key=lambda row: row[1], reverse=True)

    def _filter_documents_by_query_fit(self, chunks: List[Dict]) -> List[Dict]:
        if not chunks:
            return chunks
        stats: Dict[str, Dict[str, float]] = {}
        for chunk in chunks:
            key = self._document_key(chunk)
            row = stats.setdefault(
                key,
                {"top": 0.0, "overlap": 0.0, "anchor": 0.0, "count": 0.0, "strong_overlap_count": 0.0},
            )
            row["top"] = max(row["top"], float(chunk.get("final_score", 0.0)))
            row["overlap"] = max(row["overlap"], float(chunk.get("lexical_overlap", 0.0)))
            row["anchor"] = max(row["anchor"], float(chunk.get("anchor_overlap", 0.0)))
            row["count"] += 1.0
            if float(chunk.get("lexical_overlap", 0.0)) >= 0.35:
                row["strong_overlap_count"] += 1.0

        doc_scores: List[Tuple[str, float]] = []
        for key, row in stats.items():
            density = min(row["count"], 3.0) * 0.02
            strong_bonus = min(row["strong_overlap_count"], 3.0) * 0.03
            fit = (row["top"] * 0.56) + (row["overlap"] * 0.24) + (row["anchor"] * 0.14) + density + strong_bonus
            doc_scores.append((key, fit))
        doc_scores.sort(key=lambda x: x[1], reverse=True)
        if len(doc_scores) < 2:
            return chunks

        top_doc, top_fit = doc_scores[0]
        second_fit = doc_scores[1][1]
        top_anchor = stats[top_doc]["anchor"]
        top_overlap = stats[top_doc]["overlap"]
        second_doc = doc_scores[1][0]
        second_overlap = stats[second_doc]["overlap"]
        top_strong = stats[top_doc]["strong_overlap_count"]
        second_strong = stats[second_doc]["strong_overlap_count"]

        # If one document has clear lexical grounding and the other has none,
        # keep only the grounded one to avoid cross-file drift.
        if top_overlap >= 0.16 and second_overlap <= 0.02:
            focused = [c for c in chunks if self._document_key(c) == top_doc]
            if focused:
                return focused

        # When two docs are both relevant, prefer the one with denser strong matches.
        if top_overlap >= 0.45 and second_overlap >= 0.45:
            if (top_strong - second_strong) >= 2.0 and (top_fit - second_fit) >= 0.01:
                focused = [c for c in chunks if self._document_key(c) == top_doc]
                if focused:
                    return focused

        # Strong single-doc dominance: keep that document to avoid cross-file hallucination.
        if top_anchor >= 0.18 and top_overlap >= 0.18 and (top_fit - second_fit) >= 0.09:
            focused = [c for c in chunks if self._document_key(c) == top_doc]
            if focused:
                return focused
        return chunks

    def _select_diverse_chunks(self, ranked_chunks: List[Dict]) -> List[Dict]:
        if not ranked_chunks:
            return []

        if self.single_document_bias:
            ranked_docs = self._rank_documents(ranked_chunks)
            if ranked_docs:
                top_doc, top_score = ranked_docs[0]
                second_score = ranked_docs[1][1] if len(ranked_docs) > 1 else 0.0
                if (top_score - second_score) >= self.document_confidence_margin:
                    top_doc_chunks = [c for c in ranked_chunks if self._document_key(c) == top_doc]
                    if top_doc_chunks:
                        return top_doc_chunks[: self.max_detail_chunks]

        selected: List[Dict] = []
        seen_doc_ids = set()

        # Pass 1: prefer one strong chunk per document.
        for chunk in ranked_chunks:
            doc_id = chunk.get('metadata', {}).get('document_id')
            if doc_id and doc_id in seen_doc_ids:
                continue
            selected.append(chunk)
            if doc_id:
                seen_doc_ids.add(doc_id)
            if len(selected) >= self.max_detail_chunks:
                return selected

        # Pass 2: fill remaining slots by score.
        if len(selected) < self.max_detail_chunks:
            for chunk in ranked_chunks:
                if chunk in selected:
                    continue
                selected.append(chunk)
                if len(selected) >= self.max_detail_chunks:
                    break

        return selected

    def rerank(self, query: str, chunks: List[Dict]) -> List[Dict]:
        normalized_query = normalize_user_query(query)
        definition_query = self._is_definition_question(normalized_query)
        multi_point_query = self._query_expects_multi_point(normalized_query)
        limitations_query = self._query_asks_limitations(normalized_query)
        focus = self._query_focus(normalized_query)
        why_use_query = bool(WHY_USE_QUERY_RE.search(normalized_query))
        query_mentions_choose = bool(re.search(r"\bchoose\b|\u062a\u062e\u062a\u0627\u0631", normalized_query, flags=re.IGNORECASE))
        q_tokens = sorted(self._expanded_query_tokens(normalized_query))
        q_token_set = set(q_tokens)
        strict_lexical_for_technical = self._is_arabic(normalized_query) and bool(
            {"profile", "profiles", "policy", "policies", "sql", "script", "scripts", "privilege", "privileges", "role", "roles"}.intersection(q_token_set)
        )
        q_lower = normalize_for_search(normalized_query)
        anchor_tokens = self._query_anchor_tokens(normalized_query)

        for chunk in chunks:
            semantic_score = float(chunk.get('similarity_score', 0.0))
            content = normalize_document_text(chunk.get('content', ''))
            chunk['content'] = content
            content_window = content[:1600]
            content_tokens = set(self._tokenize(content_window))
            content_search = normalize_for_search(content_window)

            overlap = 0.0
            if q_token_set:
                overlap = len(q_token_set.intersection(content_tokens)) / len(q_token_set)

            anchor_overlap = 0.0
            if anchor_tokens:
                anchor_overlap = len(anchor_tokens.intersection(content_tokens)) / len(anchor_tokens)

            phrase_bonus = 0.0
            if len(q_lower) <= 100 and q_lower and q_lower in content_search:
                phrase_bonus = 0.10

            source = str(chunk.get('metadata', {}).get('source', '')).lower()
            source_tokens = set(self._tokenize(source))
            source_overlap = len(q_token_set.intersection(source_tokens))
            source_bonus = min(0.08, source_overlap * 0.03)
            definition_bonus = self._definition_signal_score(content) if definition_query else 0.0
            section_bias = 0.0
            if multi_point_query:
                action_hits = len(ACTION_SENTENCE_RE.findall(content[:1800]))
                section_bias += min(0.18, action_hits * 0.03)
                if limitations_query:
                    if NEGATIVE_SECTION_HINT_RE.search(content):
                        section_bias += 0.10
                else:
                    if POSITIVE_SECTION_HINT_RE.search(content):
                        section_bias += 0.10
                    if NEGATIVE_SECTION_HINT_RE.search(content):
                        section_bias -= 0.14
                if why_use_query:
                    if re.search(r"\bwhy\s+use\b|\u0644\u0645\u0627\u0630\u0627\s+\u0646\u0633\u062a\u062e\u062f\u0645", content_search, flags=re.IGNORECASE):
                        section_bias += 0.14
                    if WHY_CHOOSE_TEXT_RE.search(content_search) and not query_mentions_choose:
                        section_bias -= 0.18
            section_bias += self._focus_signal_score(focus, content_window)

            anchor_bonus = self.anchor_bonus_weight * anchor_overlap
            anchor_penalty = 0.0
            if anchor_tokens and anchor_overlap == 0.0 and overlap < 0.35 and semantic_score < self.min_high_conf_semantic:
                anchor_penalty = self.anchor_penalty_weight

            final_score = (
                (semantic_score * 0.55)
                + (overlap * 0.45)
                + phrase_bonus
                + source_bonus
                + definition_bonus
                + section_bias
                + anchor_bonus
                - anchor_penalty
            )
            chunk['lexical_overlap'] = round(overlap, 3)
            chunk['anchor_overlap'] = round(anchor_overlap, 3)
            chunk['final_score'] = round(final_score, 4)

        self._apply_document_boost(chunks)
        chunks.sort(key=lambda x: x.get('final_score', 0.0), reverse=True)

        relevant: List[Dict] = []
        for c in chunks:
            if c.get('final_score', 0.0) < self.min_relevance_score:
                continue
            overlap = float(c.get('lexical_overlap', 0.0))
            anchor = float(c.get('anchor_overlap', 0.0))
            semantic = float(c.get('similarity_score', 0.0))
            semantic_pass = semantic >= self.min_high_conf_semantic
            if strict_lexical_for_technical and semantic_pass and overlap < 0.04 and anchor < 0.04:
                semantic_pass = False
            if overlap >= self.min_chunk_lexical_overlap or semantic_pass or anchor > 0.0:
                relevant.append(c)
        if not relevant:
            if q_token_set:
                logger.info('No relevant chunks passed overlap/anchor gates for query="%s"', normalized_query[:120])
                return []
            relevant = chunks[: max(1, self.max_detail_chunks)]

        relevant = self._filter_documents_by_query_fit(relevant)
        selected = self._select_diverse_chunks(relevant)
        if definition_query and selected:
            selected = self._append_neighbor_chunks_for_definition(selected)
            selected = selected[: max(1, min(6, self.max_detail_chunks))]

        for chunk in selected:
            logger.info(
                'Selected chunk score=%.3f overlap=%.3f anchor=%.3f doc_score=%.3f source=%s',
                chunk.get('final_score', 0.0),
                chunk.get('lexical_overlap', 0.0),
                chunk.get('anchor_overlap', 0.0),
                chunk.get('document_score', 0.0),
                chunk.get('metadata', {}).get('source', '')[:60],
            )

        return selected

    def _get_cached_summary(self, key: str, fetcher: Callable[[], List[Dict]]) -> List[Dict]:
        if self.summary_cache_ttl <= 0:
            return fetcher()

        now = time.monotonic()
        with self._summary_cache_lock:
            cached = self._summary_cache.get(key)
            if cached and (now - cached['time']) < self.summary_cache_ttl:
                return cached['value']

        value = fetcher()
        with self._summary_cache_lock:
            self._summary_cache[key] = {'time': now, 'value': value}
        return value

    def build_hierarchical_context(self, intent: str, detail_chunks: List[Dict], question: str = "") -> str:
        parts = []
        definition_query = self._is_definition_question(question)
        focus = self._query_focus(question)
        max_evidence_chars = 980 if definition_query else 700
        if detail_chunks:
            top_score = float(detail_chunks[0].get('final_score', 0.0))
            focused_chunks = [
                chunk for chunk in detail_chunks
                if (top_score - float(chunk.get('final_score', 0.0))) <= self.context_score_margin
            ]
            if focused_chunks:
                detail_chunks = focused_chunks
            if focus != "general":
                detail_chunks = sorted(
                    detail_chunks,
                    key=lambda c: float(c.get('final_score', 0.0)) + self._focus_signal_score(focus, str(c.get('content', ''))[:1400]),
                    reverse=True,
                )
        max_chunks = min(len(detail_chunks), 6) if definition_query else len(detail_chunks)

        # Put detailed evidence first to avoid wrong-source bias.
        for index, chunk in enumerate(detail_chunks[:max_chunks]):
            source = chunk.get('metadata', {}).get('source', '')
            page = chunk.get('metadata', {}).get('page', '')
            text = normalize_document_text(chunk.get('content', ''))
            if len(text) > max_evidence_chars:
                clipped = text[:max_evidence_chars]
                cut = max(
                    clipped.rfind("\n"),
                    clipped.rfind(". "),
                    clipped.rfind("\u061F"),
                    clipped.rfind("\u060C"),
                    clipped.rfind(" "),
                )
                if cut > int(max_evidence_chars * 0.65):
                    clipped = clipped[:cut]
                text = clipped.rstrip()
            score = chunk.get('final_score', 0)
            parts.append(f"[Evidence {index + 1} | source={source} | page={page} | score={score}]\n{text}")

        if self.include_summaries_in_query and self.answer_mode != 'extractive':
            get_summaries = getattr(self.vector_store, 'get_summaries', None)
            if callable(get_summaries):
                global_key = self._summary_cache_key('global_summary', 'all')
                global_summaries = self._get_cached_summary(global_key, lambda: get_summaries(level='global_summary'))
                if global_summaries:
                    parts.append('[Overview Summary]\n' + global_summaries[0].get('text', ''))

                if intent != 'general':
                    section_key = self._summary_cache_key('section_summary', intent)
                    section_summaries = self._get_cached_summary(
                        section_key,
                        lambda: get_summaries(level='section_summary', category=intent),
                    )
                    if section_summaries:
                        parts.append(f"[{intent.capitalize()} Summary]\n" + section_summaries[0].get('text', ''))

        context = '\n\n---\n\n'.join(parts)
        return context[: self.max_context_chars]

    def _rewrite_query_for_retrieval(self, question: str) -> str:
        query = normalize_user_query(question, max_length=220)
        if not query:
            return query
        if not self.enable_agentic_rag or not self.enable_agentic_query_rewrite:
            return query
        if not OLLAMA_AVAILABLE or not self.llm_client:
            return query
        if len(query) < 4:
            return query

        model_name = self._model_for_query(query)
        prompt = QUERY_REWRITE_PROMPT.format(question=query)
        try:
            rewritten = self._llm_generate(
                prompt,
                max_tokens=min(self.agentic_rewrite_max_tokens, self.answer_max_tokens),
                model_name=model_name,
                timeout_seconds=min(self.agentic_rewrite_timeout_seconds, self.max_response_seconds),
                num_ctx=min(self.llm_num_ctx, 1024),
            )
        except Exception as exc:
            logger.info('Agentic query rewrite skipped: %s', exc)
            return query

        rewritten = normalize_user_query(rewritten, max_length=220)
        if not rewritten:
            return query

        if self._is_arabic(query) and not self._is_arabic(rewritten):
            return query
        return rewritten

    def _cross_language_query_hint(self, question: str) -> str:
        query = normalize_user_query(question, max_length=220)
        if not query:
            return ""
        if not self.enable_cross_language_query_hint:
            return ""
        if not self._is_arabic(query):
            return ""
        # If the query already includes Latin tokens, avoid extra rewrite.
        if re.search(r"[A-Za-z]{3,}", query):
            return ""
        if not OLLAMA_AVAILABLE or not self.llm_client:
            return ""

        prompt = CROSS_LANGUAGE_QUERY_HINT_PROMPT.format(question=query)
        model_name = self.model or self._model_for_query(query)
        try:
            hint_raw = self._llm_generate(
                prompt,
                max_tokens=min(self.cross_language_hint_max_tokens, self.answer_max_tokens),
                model_name=model_name,
                timeout_seconds=min(self.cross_language_hint_timeout_seconds, self.max_response_seconds),
                num_ctx=min(self.llm_num_ctx, 768),
            )
        except Exception as exc:
            logger.info('Cross-language retrieval hint skipped: %s', exc)
            return ""

        hint_norm = normalize_for_search(hint_raw)
        english_tokens: List[str] = []
        for token in TOKEN_RE.findall(hint_norm):
            if not re.fullmatch(r"[a-z0-9_]+", token):
                continue
            if token in EN_STOPWORDS:
                continue
            if len(token) < 3:
                continue
            if token not in english_tokens:
                english_tokens.append(token)
            if len(english_tokens) >= 8:
                break
        return " ".join(english_tokens).strip()

    def _context_quality_signals(self, chunks: List[Dict], context: str) -> Dict[str, float]:
        if not chunks or not context:
            return {'score': 0.0, 'top_score': 0.0, 'top_overlap': 0.0, 'chunk_count': 0.0}

        top_score = float(max((c.get('final_score', 0.0) for c in chunks), default=0.0))
        top_overlap = float(max((c.get('lexical_overlap', 0.0) for c in chunks), default=0.0))
        chunk_factor = min(len(chunks), self.max_detail_chunks) / max(1, self.max_detail_chunks)
        blended_score = (top_score * 0.65) + (top_overlap * 0.25) + (chunk_factor * 0.10)
        return {
            'score': round(blended_score, 4),
            'top_score': round(top_score, 4),
            'top_overlap': round(top_overlap, 4),
            'chunk_count': float(len(chunks)),
        }

    def _intent_thresholds(self, intent: str) -> Dict[str, float]:
        intent_key = (intent or 'general').lower()
        if intent_key == 'pricing':
            return {
                'min_chunks': float(self.agentic_min_chunks_pricing),
                'min_top_score': self.agentic_min_top_score_pricing,
                'min_overlap': self.agentic_min_overlap_pricing,
            }
        if intent_key == 'features':
            return {
                'min_chunks': float(self.agentic_min_chunks_features),
                'min_top_score': self.agentic_min_top_score_features,
                'min_overlap': self.agentic_min_overlap_features,
            }
        if intent_key == 'support':
            return {
                'min_chunks': float(self.agentic_min_chunks_support),
                'min_top_score': self.agentic_min_top_score_support,
                'min_overlap': self.agentic_min_overlap_support,
            }
        return {
            'min_chunks': float(self.agentic_min_chunks),
            'min_top_score': self.agentic_min_top_score,
            'min_overlap': self.agentic_min_overlap,
        }

    def _is_context_sufficient(self, chunks: List[Dict], context: str, intent: str = 'general') -> bool:
        thresholds = self._intent_thresholds(intent)
        min_chunks = thresholds['min_chunks']
        min_top_score = thresholds['min_top_score']
        min_overlap = thresholds['min_overlap']
        signals = self._context_quality_signals(chunks, context)
        if signals['chunk_count'] < min_chunks:
            return False
        if signals['top_overlap'] >= min_overlap:
            return True
        if (
            signals['top_score'] >= (min_top_score + 0.10)
            and signals['top_overlap'] >= max(0.02, min_overlap * 0.45)
        ):
            return True
        return False

    def _is_low_confidence_for_extractive(self, chunks: List[Dict], context: str, intent: str) -> bool:
        signals = self._context_quality_signals(chunks, context)
        if signals['chunk_count'] <= 0:
            return True
        strong_overlap_chunks = sum(1 for c in (chunks or []) if float(c.get('lexical_overlap', 0.0)) >= 0.18)
        # If we have multiple lexically grounded chunks, allow extractive answer
        # even when top_score is slightly below the strict cutoff.
        if signals['top_score'] < self.extractive_low_conf_top_score:
            if not (signals['top_overlap'] >= 0.18 and strong_overlap_chunks >= 2):
                return True
        if signals['top_overlap'] < self.extractive_low_conf_overlap:
            return True
        return not self._is_context_sufficient(chunks, context, intent=intent)

    def _candidate_retrieval_queries(self, question: str) -> List[str]:
        base_query = normalize_user_query(question)
        if not base_query:
            return []
        if not self.enable_agentic_rag:
            return [base_query]

        base_tokens = self._expanded_query_tokens(base_query)
        technical_profile_query = self._is_arabic(base_query) and any(
            tok in base_tokens
            for tok in {"profile", "profiles", "policy", "policies", "sql", "script", "scripts", "privilege", "privileges", "role", "roles"}
        )
        if technical_profile_query:
            ordered = [self._expand_query_for_retrieval(base_query), base_query]
            cross_lang_hint = ""
        else:
            rewritten = self._rewrite_query_for_retrieval(base_query)
            cross_lang_hint = self._cross_language_query_hint(base_query)
            merged_cross_lang = f"{base_query} {cross_lang_hint}".strip() if cross_lang_hint else ""
            # Keep original query first to avoid hint drift; use hints as fallback only.
            ordered = [base_query, rewritten, merged_cross_lang, cross_lang_hint]
        unique: List[str] = []
        seen: Set[str] = set()
        max_attempts = self.agentic_max_retrieval_attempts
        if cross_lang_hint:
            max_attempts = max(max_attempts, 2)
        for candidate in ordered:
            key = normalize_for_search(candidate)
            if not key or key in seen:
                continue
            seen.add(key)
            unique.append(candidate)
            if len(unique) >= max_attempts:
                break
        return unique or [base_query]

    def _agentic_retrieve_context(self, question: str, intent: str) -> Tuple[List[Dict], str]:
        candidates = self._candidate_retrieval_queries(question)
        best_chunks: List[Dict] = []
        best_context = ""
        best_score = -1.0
        prefer_overlap = self._is_arabic(question)

        for idx, retrieval_query in enumerate(candidates, start=1):
            chunks = self.retrieve(retrieval_query, k=self.retrieval_k)
            chunks = self.rerank(retrieval_query, chunks)
            context = self.build_hierarchical_context(intent, chunks, question)
            signals = self._context_quality_signals(chunks, context)

            threshold_view = self._intent_thresholds(intent)
            logger.info(
                'Agentic retrieval attempt=%d/%d intent=%s score=%.3f top=%.3f overlap=%.3f thresholds=(chunks>=%.0f top>=%.2f overlap>=%.2f) query="%s"',
                idx,
                len(candidates),
                intent,
                signals['score'],
                signals['top_score'],
                signals['top_overlap'],
                threshold_view['min_chunks'],
                threshold_view['min_top_score'],
                threshold_view['min_overlap'],
                retrieval_query[:120],
            )

            candidate_score = float(signals['score'])
            if prefer_overlap:
                candidate_score = (signals['top_overlap'] * 0.68) + (signals['score'] * 0.32)
                if signals['top_overlap'] <= 0.01:
                    candidate_score -= 0.22

            if candidate_score > best_score:
                best_score = candidate_score
                best_chunks = chunks
                best_context = context

            if self._is_context_sufficient(chunks, context, intent=intent):
                return chunks, context

        return best_chunks, best_context

    def _self_check_answer_grounding(self, question: str, context: str, answer: str) -> Tuple[bool, str]:
        if not self.enable_agentic_rag or not self.enable_agentic_self_check:
            return True, 'disabled'
        if not answer:
            return False, 'empty answer'
        if self._is_abstention_answer(answer):
            return True, 'abstention'
        if not OLLAMA_AVAILABLE or not self.llm_client:
            return True, 'llm unavailable'

        prompt = SELF_CHECK_PROMPT.format(context=context[:2600], question=question, answer=answer[:900])
        model_name = self._model_for_query(question)
        try:
            verdict_text = self._llm_generate(
                prompt,
                max_tokens=min(self.agentic_self_check_max_tokens, self.answer_max_tokens),
                model_name=model_name,
                timeout_seconds=min(self.agentic_self_check_timeout_seconds, self.max_response_seconds),
                num_ctx=min(self.llm_num_ctx, 1024),
            ).strip()
        except Exception as exc:
            logger.info('Agentic self-check skipped: %s', exc)
            return True, 'self-check unavailable'

        match = SELF_CHECK_VERDICT_RE.search(verdict_text)
        if not match:
            lowered = verdict_text.lower()
            if 'yes' in lowered:
                return True, verdict_text[:200]
            if 'no' in lowered:
                return False, verdict_text[:200]
            return True, 'unparseable verdict'

        is_grounded = match.group(1).upper() == 'YES'
        reason = verdict_text[:200]
        return is_grounded, reason

    def _build_english_extractive_response(self, snippet: str, *, source_text: str = "", query: str = "") -> str:
        value = normalize_document_text(snippet)
        compact = re.sub(r"\s+", " ", value).strip()
        if len(compact) > 260:
            compact = compact[:260].rsplit(' ', 1)[0].strip() + '...'
        return compact

    def _is_structured_technical_answer(self, text: str) -> bool:
        value = normalize_document_text(text or "")
        if not value:
            return False
        lines = [ln.strip() for ln in value.splitlines() if ln.strip()]
        if len(lines) < 2:
            return False
        if SQL_TECHNICAL_RE.search(value):
            return True
        if value.count(";") >= 3:
            return True
        return False

    def _refine_multiline_answer(self, query: str, answer: str) -> str:
        value = normalize_document_text(answer or "")
        if not value or "\n" not in value:
            if value:
                query_has_sql = bool(re.search(r"\b(?:sql|script|scripts|create|grant)\b", normalize_for_search(query)))
                if not query_has_sql:
                    value = re.sub(
                        r"\s+\d{1,2}\.\s+(?:[A-Za-z][A-Za-z0-9 _\-/]{1,80}|[\u0600-\u06FF][\u0600-\u06FF0-9 _\-/]{1,80})\s*$",
                        "",
                        value,
                        flags=re.IGNORECASE,
                    ).strip()
            return value

        total_lines = len([ln for ln in value.splitlines() if ln.strip()])
        q_tokens = self._expanded_query_tokens(query)
        q_token_set = set(q_tokens)
        query_norm = normalize_for_search(query)
        query_has_profile_policy = any(
            tok in q_token_set for tok in {"profile", "profiles", "policy", "policies", "privilege", "privileges", "role", "roles"}
        )
        query_has_sql = bool(re.search(r"\b(?:sql|script|scripts|create|grant)\b", query_norm)) or any(
            tok in q_token_set for tok in {"sql", "script", "scripts", "create", "grant"}
        )
        overlap_floor = 0.10 if self._is_arabic(query) else 0.12

        kept: List[str] = []
        for raw in value.splitlines():
            line = re.sub(r"\s+", " ", raw).strip()
            if not line:
                continue
            if PROMPT_LEAK_RE.search(line):
                continue
            if (not query_has_sql) and SECTION_HEADING_LINE_RE.search(line):
                continue

            overlap = self._line_overlap_score(q_tokens, line) if q_tokens else 0.0
            has_profile_policy_line = bool(re.search(r"\b(?:profile|profiles|policy|policies)\b", normalize_for_search(line)))
            sql_line = bool(SQL_TECHNICAL_RE.search(line))

            keep = overlap >= overlap_floor
            if query_has_profile_policy and has_profile_policy_line:
                keep = True
            if query_has_profile_policy and sql_line and overlap >= 0.08:
                keep = True
            if query_has_profile_policy and sql_line and re.search(r"\bPROFILE\b", line, flags=re.IGNORECASE):
                keep = True
            if query_has_sql and sql_line:
                keep = True

            if keep:
                kept.append(line)

        if len(kept) >= 2 or (total_lines <= 3 and len(kept) >= 1):
            return "\n".join(kept)
        if query_has_profile_policy and len(kept) >= 1:
            return "\n".join(kept)
        return value

    def _lexical_grounding_check(self, question: str, answer: str, context: str, intent: str) -> Tuple[bool, str]:
        if not self.enable_lexical_grounding_check:
            return True, 'lexical check disabled'
        if not answer or not context:
            return False, 'missing answer/context'
        if self._is_abstention_answer(answer):
            return True, 'abstention'

        answer_tokens = set(self._expanded_query_tokens(answer))
        context_tokens = set(self._expanded_query_tokens(context[:5000]))
        if not answer_tokens or not context_tokens:
            return False, 'empty token set'

        overlap = len(answer_tokens.intersection(context_tokens)) / max(1, len(answer_tokens))
        strict_mode = intent in {'pricing', 'features', 'support'}
        min_required = self.min_answer_context_coverage_strict if strict_mode else self.min_answer_context_coverage

        if overlap >= min_required:
            return True, f'coverage={overlap:.2f}'
        return False, f'low coverage={overlap:.2f} < {min_required:.2f}'

    def _model_for_query(self, query: str) -> str:
        if self._is_arabic(query) and self.model_arabic:
            return self.model_arabic
        return self.model

    def _run_with_timeout(self, fn: Callable[[], Any], timeout_seconds: float):
        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(fn)
        try:
            result = future.result(timeout=timeout_seconds)
        except FutureTimeoutError as exc:
            future.cancel()
            executor.shutdown(wait=False, cancel_futures=True)
            raise TimeoutError(f"LLM call exceeded timeout of {timeout_seconds:.1f}s") from exc
        except Exception:
            executor.shutdown(wait=False, cancel_futures=True)
            raise
        else:
            executor.shutdown(wait=True, cancel_futures=True)
            return result

    def _llm_generate(
        self,
        prompt: str,
        max_tokens: int,
        model_name: str,
        timeout_seconds: float | None = None,
        num_ctx: int | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
    ) -> str:
        timeout_seconds = timeout_seconds or self.max_response_seconds
        effective_num_ctx = num_ctx or self.llm_num_ctx
        if model_name and 'llama3' in model_name.lower():
            effective_num_ctx = min(effective_num_ctx, 2048)

        effective_temperature = self.llm_temperature if temperature is None else float(temperature)
        effective_top_p = self.llm_top_p if top_p is None else float(top_p)
        started = time.perf_counter()
        response = self._run_with_timeout(
            lambda: self.llm_client.generate(
                model=model_name,
                prompt=prompt,
                keep_alive='10m',
                options={
                    'temperature': effective_temperature,
                    'num_predict': max_tokens,
                    'top_p': effective_top_p,
                    'num_ctx': effective_num_ctx,
                },
            ),
            timeout_seconds=float(timeout_seconds),
        )
        duration = time.perf_counter() - started
        logger.info('LLM generate completed in %.2fs using model=%s', duration, model_name)
        return response['response'].strip()

    def _context_blocks(self, context: str) -> List[List[str]]:
        blocks: List[List[str]] = []
        raw_blocks = [b.strip() for b in (context or "").split('\n\n---\n\n') if b.strip()]
        for block in raw_blocks:
            lines = [line.strip() for line in block.splitlines() if line.strip()]
            body = lines[1:] if (lines and lines[0].startswith('[Evidence')) else lines
            if body:
                blocks.append(body)
        return blocks

    def _line_overlap_score(self, query_tokens: Set[str], line: str) -> float:
        if not query_tokens:
            return 0.0
        line_tokens = set(self._tokenize(line))
        if not line_tokens:
            return 0.0
        return len(query_tokens.intersection(line_tokens)) / max(1, len(query_tokens))

    def _extract_section_for_topic(self, query: str, context: str, max_lines: int = 10) -> str:
        topic = self._extract_topic_from_query(query)
        if not topic:
            return ""
        query_norm = normalize_for_search(query)
        query_has_policy_sql_terms = bool(
            re.search(r"\b(?:profile|profiles|policy|policies|privilege|privileges|role|roles|tablespace|sql)\b", query_norm)
        )
        topic_token_set = set(self._expanded_query_tokens(topic))
        topic_token_set.update(self._expanded_query_tokens(query))
        topic_tokens = [tok for tok in sorted(topic_token_set) if tok not in GENERIC_QUERY_TOKENS]
        if not topic_tokens:
            topic_tokens = self._tokenize(query)[:4]
        if not topic_tokens:
            return ""

        blocks = self._context_blocks(context)
        candidates: List[Tuple[float, str]] = []
        focus = self._query_focus(query)
        meta_noise_re = re.compile(r"\b(?:presented by|course|university|date|academic presentation)\b", re.IGNORECASE)

        for lines in blocks:
            for idx, raw in enumerate(lines):
                line = re.sub(r"\s+", " ", raw).strip()
                if len(line) < 4:
                    continue
                overlap = self._line_overlap_score(set(topic_tokens), line)
                line_norm = normalize_for_search(line)
                is_why_choose_line = bool(WHY_CHOOSE_TEXT_RE.search(line_norm))
                is_definition_anchor_line = bool(
                    ("what is" in line_norm)
                    or ("\u0645\u0627 \u0647\u0648" in line_norm)
                    or ("\u0645\u0627 \u0647\u064a" in line_norm)
                    or ("\u062a\u0639\u0631\u064a\u0641" in line_norm)
                )
                question_anchor = bool(
                    is_definition_anchor_line
                    or (line.endswith("?") and not is_why_choose_line)
                )
                if focus == "definition" and is_why_choose_line:
                    continue
                technical_line = bool(
                    re.search(r"\b(?:profile|profiles|policy|policies|privilege|privileges|role|roles|tablespace|sql|create|grant)\b", line_norm)
                )
                min_overlap = 0.34
                if query_has_policy_sql_terms and technical_line:
                    min_overlap = 0.18
                if self._is_arabic(query):
                    min_overlap = min(min_overlap, 0.20)
                    if query_has_policy_sql_terms and technical_line:
                        min_overlap = min(min_overlap, 0.08)
                if overlap < min_overlap and not question_anchor:
                    continue

                collected: List[str] = [line]
                for next_line in lines[idx + 1:]:
                    value = re.sub(r"\s+", " ", next_line).strip()
                    if not value:
                        continue
                    if len(collected) >= max_lines:
                        break
                    if len(collected) >= 2 and SECTION_HEADING_LINE_RE.search(value):
                        break
                    if len(collected) >= 3 and (self._is_heading_like_sentence(value) or SECTION_BREAK_RE.search(value)):
                        break
                    if PROMPT_LEAK_RE.search(value):
                        continue
                    collected.append(value)
                text = "\n".join(collected).strip()
                if len(text) < 40:
                    continue

                score = overlap
                if question_anchor:
                    score += 0.22
                score += min(0.18, max(0.0, self._focus_signal_score(focus, text)))
                if focus == "definition":
                    if is_definition_anchor_line:
                        score += 0.14
                    if DEFINITION_TEXT_HINT_RE.search(text):
                        score += 0.18
                    if meta_noise_re.search(text):
                        score -= 0.15
                candidates.append((score, text))

        if not candidates:
            return ""
        candidates.sort(key=lambda row: row[0], reverse=True)
        return candidates[0][1]

    def _extract_matched_lines(self, query: str, context: str, max_lines: int = 6) -> str:
        blocks = self._context_blocks(context)
        if not blocks:
            return ""
        q_tokens = self._expanded_query_tokens(query)
        query_norm = normalize_for_search(query)
        query_has_policy_sql_terms = bool(
            re.search(r"\b(?:profile|profiles|policy|policies|privilege|privileges|role|roles|tablespace|sql|script|create|grant)\b", query_norm)
        )
        focus = self._query_focus(query)
        definition_query = self._is_definition_question(query)
        multi_point_query = self._query_expects_multi_point(query)
        scored: List[Tuple[float, str]] = []
        query_has_explicit_sql_heading_need = bool(re.search(r"\b(?:sql|script|scripts)\b", query_norm))

        for lines in blocks:
            for raw in lines:
                line = re.sub(r"\s+", " ", raw).strip()
                if len(line) < 6:
                    continue
                if SECTION_HEADING_LINE_RE.search(line) and not query_has_explicit_sql_heading_need:
                    continue
                if self._is_heading_like_sentence(line) and not self._is_definition_question(query):
                    continue
                overlap = self._line_overlap_score(q_tokens, line)
                score = overlap + (self._focus_signal_score(focus, line) * 0.55)
                line_norm = normalize_for_search(line)
                technical_line = bool(
                    re.search(r"\b(?:profile|profiles|policy|policies|privilege|privileges|role|roles|tablespace|sql|script|create|grant)\b", line_norm)
                )
                if query_norm and query_norm in line_norm:
                    score += 0.25
                if re.search(r"^\s*(?:[-\u2022]|\d{1,2}[\)\.\-])\s*", raw):
                    score += 0.07
                if query_has_policy_sql_terms and technical_line:
                    score += 0.12
                if definition_query:
                    word_count = len(re.findall(r"[A-Za-z0-9]+|[\u0600-\u06FF]+", line))
                    if 2 <= word_count <= 7 and re.search(r"[A-Za-z\u0600-\u06FF]", line):
                        score += 0.12
                # Drop very short fragment-like continuations (common OCR slicing noise).
                if (
                    len(line) <= 34
                    and re.match(r"^[a-z]", line)
                    and not SQL_TECHNICAL_RE.search(line)
                    and not re.search(r"[\u0600-\u06FF]", line)
                ):
                    score -= 0.28
                if CONTINUATION_LINE_RE.search(line):
                    score -= 0.12
                scored.append((score, line))

        if not scored:
            return ""
        scored.sort(key=lambda row: row[0], reverse=True)

        selected: List[str] = []
        seen = set()
        min_required_score = self.strict_extractive_line_overlap
        if definition_query or multi_point_query:
            min_required_score = min(min_required_score, 0.08)
        if self._is_arabic(query):
            min_required_score = min(min_required_score, 0.10)
            if query_has_policy_sql_terms:
                min_required_score = min(min_required_score, 0.06)
        for score, line in scored:
            if score < min_required_score:
                continue
            key = normalize_for_search(line)
            if not key or key in seen:
                continue
            seen.add(key)
            selected.append(line)
            if len(selected) >= max_lines:
                break

        if not selected:
            return ""
        return "\n".join(selected)

    def _closest_excerpt(self, query: str, context: str, max_chars: int = 520) -> str:
        blocks = self._context_blocks(context)
        if not blocks:
            return ""
        q_tokens = self._expanded_query_tokens(query)
        best_text = ""
        best_score = 0.0
        for lines in blocks:
            block_text = re.sub(r"\s+", " ", " ".join(lines)).strip()
            if not block_text:
                continue
            score = self._line_overlap_score(q_tokens, block_text)
            score += min(0.18, max(0.0, self._focus_signal_score(self._query_focus(query), block_text)))
            if score > best_score:
                best_score = score
                best_text = block_text
        if best_score < self.closest_excerpt_min_score:
            return ""
        if len(best_text) > max_chars:
            best_text = best_text[:max_chars].rsplit(" ", 1)[0].strip() + "..."
        return best_text

    def _extend_truncated_section(self, section: str, context: str, *, max_extra_lines: int = 8) -> str:
        value = normalize_document_text(section or "").strip()
        if not value:
            return value
        if value[-1:] in ".!?\u061f":
            return value
        if not re.search(r"(?:\bto\b|\band\b|\bwith\b|\bor\b|[\u0627-\u064a]+)$", value.splitlines()[-1].strip(), re.IGNORECASE):
            return value

        normalized_context = normalize_document_text(context or "")
        pos = normalized_context.find(value)
        if pos < 0:
            return value
        tail = normalized_context[pos + len(value):]
        extra_lines: List[str] = []
        for raw in tail.splitlines():
            line = re.sub(r"\s+", " ", raw).strip()
            if not line:
                continue
            if line.startswith("[Evidence"):
                if extra_lines:
                    break
                continue
            if len(line) < 4:
                continue
            if self._is_heading_like_sentence(line) and not re.search(r"\b(?:for all skill levels|multi-application support|enhanced testing efficiency)\b", line, re.IGNORECASE):
                if extra_lines:
                    break
                continue
            extra_lines.append(line)
            if len(extra_lines) >= max_extra_lines:
                break
            if line[-1:] in ".!?\u061f" and len(extra_lines) >= 2:
                break

        if not extra_lines:
            return value
        return f"{value}\n" + "\n".join(extra_lines)

    def _extend_structured_block(self, section: str, context: str, *, max_extra_lines: int = 28) -> str:
        value = normalize_document_text(section or "").strip()
        if not value:
            return value

        normalized_context = normalize_document_text(context or "")
        pos = normalized_context.find(value)
        if pos < 0:
            return value

        extra_lines: List[str] = []
        tail = normalized_context[pos + len(value):]
        sql_or_heading_re = re.compile(
            r"(?:\b(?:CREATE|GRANT|ALTER|DROP|INSERT|UPDATE|DELETE|SELECT)\b|"
            r"\b(?:SQL\s+Scripts?|Creation of|Privileges|Roles|Users|Profiles|Tablespaces)\b)",
            flags=re.IGNORECASE,
        )
        hard_break_re = re.compile(
            r"^(?:\[\s*Evidence|\[\s*Overview|\d+\.\s*(?:introduction|overview|conclusion)\b)",
            flags=re.IGNORECASE,
        )
        for raw in tail.splitlines():
            line = re.sub(r"\s+", " ", raw).strip()
            if not line:
                continue
            if hard_break_re.search(line):
                break
            if len(extra_lines) >= max_extra_lines:
                break
            if sql_or_heading_re.search(line):
                extra_lines.append(line)
                continue
            # stop after we've already started collecting and hit unrelated text
            if extra_lines:
                break

        if not extra_lines:
            return value
        return f"{value}\n" + "\n".join(extra_lines)

    def _strict_extractive_answer(self, query: str, context: str) -> str:
        structured_query = bool(re.search(r"\bsql\b|\bscript(?:s)?\b|\bcreate\b|\bgrant\b", normalize_for_search(query), flags=re.IGNORECASE))
        atomic = self._extract_focus_atomic_answer(query, context)
        if atomic:
            return atomic
        section = self._extract_section_for_topic(query, context)
        if section:
            if structured_query:
                section = self._extend_structured_block(section, context)
            if self._is_definition_question(query) or self._query_expects_multi_point(query):
                section = self._extend_truncated_section(section, context)
            if self._is_definition_question(query) or self._query_expects_multi_point(query) or structured_query:
                matched = self._extract_matched_lines(query, context, max_lines=20 if structured_query else 10)
                if matched and len(matched) > (len(section) + 24):
                    return matched
            return section
        matched = self._extract_matched_lines(query, context, max_lines=20 if structured_query else 6)
        if matched:
            return matched
        closest = self._closest_excerpt(query, context)
        if closest:
            return closest
        return ""

    def _extractive_fallback_answer(self, query: str, context: str) -> str:
        strict = self._strict_extractive_answer(query, context)
        if strict:
            return normalize_document_text(strict).strip()
        closest = self._closest_excerpt(query, context)
        if closest:
            return normalize_document_text(closest).strip()
        return self._no_info_message(query)

    def _postprocess_answer(self, query: str, answer: str, *, context: str = "") -> str:
        cleaned = sanitize_generated_answer(query, answer)
        if not cleaned:
            return ""
        cleaned = self._refine_multiline_answer(query, cleaned)
        return cleaned

    def _contains_unseen_url(self, answer: str, context: str) -> bool:
        answer_urls = {u.rstrip(".,);]") for u in URL_RE.findall(answer or "")}
        if not answer_urls:
            return False
        context_urls = {u.rstrip(".,);]") for u in URL_RE.findall(context or "")}
        for url in answer_urls:
            if url not in context_urls:
                return True
        return False

    def _light_sanitize_stream_chunk(self, chunk: str) -> str:
        value = (chunk or "").replace("\r\n", "\n").replace("\r", "\n")
        if not value:
            return ""

        value = STREAM_ZERO_WIDTH_RE.sub("", value)
        value = STREAM_REPLACEMENT_RE.sub(" ", value)
        value = STREAM_CONTROL_CHARS_RE.sub(" ", value)
        value = STREAM_NOISE_SYMBOLS_RE.sub(" ", value)
        value = re.sub(r"\s+([,;:.!?])", r"\1", value)
        value = STREAM_MULTI_SPACE_RE.sub(" ", value)
        return value

    def _finalize_stream_answer(self, query: str, raw_answer: str, *, context: str = "") -> str:
        if not raw_answer:
            return ""
        final_answer = self._postprocess_answer(query, raw_answer, context=context)
        if self._is_abstention_answer(final_answer):
            return self._extractive_fallback_answer(query, context)
        if self._contains_unseen_url(final_answer, context):
            return self._extractive_fallback_answer(query, context)
        final_answer = self._ensure_query_language(query, final_answer)
        final_answer = self._postprocess_answer(query, final_answer, context=context)
        if self._is_abstention_answer(final_answer):
            return self._extractive_fallback_answer(query, context)
        if self._contains_unseen_url(final_answer, context):
            return self._extractive_fallback_answer(query, context)
        focus = self._query_focus(query)
        if focus in {"definition", "procedure", "time", "person", "location", "quantity", "capability"}:
            if not self._answer_matches_focus(focus, final_answer):
                extractive = self._extractive_fallback_answer(query, context)
                if extractive and not self._is_abstention_answer(extractive) and self._answer_matches_focus(focus, extractive):
                    final_answer = extractive
        if self._query_expects_multi_point(query):
            generated_points = self._answer_point_count(final_answer)
            extractive = self._extractive_fallback_answer(query, context)
            if extractive and not self._is_abstention_answer(extractive):
                extractive_points = self._answer_point_count(extractive)
                if extractive_points >= 3 or extractive_points >= generated_points:
                    final_answer = extractive
        return final_answer

    def _needs_arabic_rewrite(self, query: str, answer: str) -> bool:
        if not self.enable_arabic_rewrite:
            return False
        if not self._is_arabic(query):
            return False
        if len(answer.strip()) < 15:
            return False
        if len(answer) > 700:
            return False
        if self._arabic_ratio(answer) < self.min_arabic_answer_ratio:
            return True
        return bool(MIXED_SCRIPT_RE.search(answer))

    def _rewrite_in_arabic(self, answer: str, query: str, *, context: str = "") -> str:
        model_name = self._model_for_query(query)
        prompt_lines = [
            "Rewrite the text into clear Modern Standard Arabic only.",
            "Do not add new facts.",
            "Return only the final answer text with no headings, no notes, and no translation disclaimers.",
            "Keep technical terms, product names, and acronyms exactly as they appear in context.",
        ]

        prompt = "\n".join(prompt_lines) + f"\n\nText:\n{answer}\n\nArabic rewrite:"
        try:
            rewritten = self._llm_generate(
                prompt,
                max_tokens=min(self.rewrite_max_tokens, self.answer_max_tokens),
                model_name=model_name,
                timeout_seconds=min(self.rewrite_timeout_seconds, self.max_response_seconds),
            )
            return self._postprocess_answer(query, rewritten, context=context)
        except Exception:
            return self._postprocess_answer(query, answer, context=context)

    def generate(self, query: str, context: str) -> str:
        if not OLLAMA_AVAILABLE or not self.llm_client:
            return self._service_unavailable_message(query)

        prompt = RAG_PROMPT_TEMPLATE.format(context=context, question=query)
        model_name = self._model_for_query(query)
        definition_query = self._is_definition_question(query)
        primary_tokens = min(self.answer_max_tokens, 160) if definition_query else self.answer_max_tokens
        primary_timeout = min(self.max_response_seconds, 35.0) if definition_query else self.max_response_seconds
        primary_num_ctx = min(self.llm_num_ctx, 1280) if definition_query else self.llm_num_ctx
        primary_started = time.perf_counter()
        try:
            answer = self._llm_generate(
                prompt,
                max_tokens=primary_tokens,
                model_name=model_name,
                timeout_seconds=primary_timeout,
                num_ctx=primary_num_ctx,
            )
        except TimeoutError as exc:
            logger.warning('Primary LLM generation timed out, retrying with reduced limits: %s', exc)
            retry_tokens = max(72, min(primary_tokens, 96))
            retry_num_ctx = max(768, min(primary_num_ctx, 960))
            retry_timeout = max(10.0, min(primary_timeout * 0.60, 22.0))
            try:
                answer = self._llm_generate(
                    prompt,
                    max_tokens=retry_tokens,
                    model_name=model_name,
                    timeout_seconds=retry_timeout,
                    num_ctx=retry_num_ctx,
                )
            except Exception as retry_exc:
                logger.error('LLM retry failed: %s', retry_exc)
                return self._extractive_fallback_answer(query, context)
        except Exception as exc:
            logger.error('Failed to generate response: %s', exc)
            return self._extractive_fallback_answer(query, context)

        if self._is_abstention_answer(answer):
            # If model abstains, return best extractive snippet instead of immediate NO_INFO.
            return self._extractive_fallback_answer(query, context)

        primary_duration = time.perf_counter() - primary_started
        should_rewrite = self._needs_arabic_rewrite(query, answer)
        if should_rewrite and primary_duration <= self.max_primary_seconds_before_skip_rewrite:
            answer = self._rewrite_in_arabic(answer, query, context=context).strip()
        elif should_rewrite:
            logger.info(
                'Skipping Arabic rewrite due to latency budget: primary_duration=%.2fs threshold=%.2fs',
                primary_duration,
                self.max_primary_seconds_before_skip_rewrite,
            )

        final_answer = self._postprocess_answer(query, answer, context=context)
        if self._is_abstention_answer(final_answer):
            return self._extractive_fallback_answer(query, context)
        if self._contains_unseen_url(final_answer, context):
            return self._extractive_fallback_answer(query, context)
        final_answer = self._ensure_query_language(query, final_answer)
        final_answer = self._postprocess_answer(query, final_answer, context=context)
        if self._is_abstention_answer(final_answer):
            return self._extractive_fallback_answer(query, context)
        if self._contains_unseen_url(final_answer, context):
            return self._extractive_fallback_answer(query, context)
        focus = self._query_focus(query)
        if focus in {"definition", "procedure", "time", "person", "location", "quantity", "capability"}:
            if not self._answer_matches_focus(focus, final_answer):
                extractive = self._extractive_fallback_answer(query, context)
                if extractive and not self._is_abstention_answer(extractive) and self._answer_matches_focus(focus, extractive):
                    final_answer = extractive
        if self._query_expects_multi_point(query):
            generated_points = self._answer_point_count(final_answer)
            extractive = self._extractive_fallback_answer(query, context)
            if extractive and not self._is_abstention_answer(extractive):
                extractive_points = self._answer_point_count(extractive)
                if extractive_points >= 3 or extractive_points >= generated_points:
                    final_answer = extractive
        return final_answer

    def generate_stream(self, query: str, context: str, state: StreamAnswerState | None = None):
        stream_state = state or StreamAnswerState()

        if not OLLAMA_AVAILABLE or not self.llm_client:
            message = self._service_unavailable_message(query)
            stream_state.tokens.append(message)
            stream_state.final_answer = self._finalize_stream_answer(query, stream_state.raw_answer, context=context)
            yield message
            return

        model_name = self._model_for_query(query)
        prompt = RAG_PROMPT_TEMPLATE.format(context=context, question=query)

        try:
            response = self.llm_client.generate(
                model=model_name,
                prompt=prompt,
                stream=True,
                keep_alive='10m',
                options={
                    'temperature': self.llm_temperature,
                    'num_predict': self.answer_max_tokens,
                    'top_p': self.llm_top_p,
                    'num_ctx': self.llm_num_ctx,
                },
            )
            for chunk in response:
                if not chunk.get('response'):
                    continue

                cleaned_chunk = self._light_sanitize_stream_chunk(chunk['response'])
                if not cleaned_chunk:
                    continue

                stream_state.tokens.append(cleaned_chunk)
                yield cleaned_chunk

            finalized = self._finalize_stream_answer(query, stream_state.raw_answer, context=context)
            stream_state.final_answer = finalized or stream_state.raw_answer.strip()
        except Exception as exc:
            logger.error('Streaming failed: %s', exc)
            message = self._service_unavailable_message(query)
            stream_state.tokens.append(message)
            stream_state.final_answer = self._finalize_stream_answer(query, stream_state.raw_answer, context=context)
            yield message

    def generate_summary(self, text: str, max_chars: int = 3000) -> str:
        if not OLLAMA_AVAILABLE or not self.llm_client:
            return ''

        try:
            prompt = SUMMARY_PROMPT.format(text=text[:max_chars])
            model_name = self.model
            return self._llm_generate(
                prompt,
                max_tokens=self.summary_max_tokens,
                model_name=model_name,
                timeout_seconds=self.max_summary_seconds,
            )
        except Exception as exc:
            logger.error('Summary generation failed: %s', exc)
            return ''

    def query(self, question: str, stream: bool = False) -> Dict[str, Any]:
        question = normalize_user_query(question)
        if not question:
            return {'answer': 'Please send a valid question.', 'sources': [], 'chunks_used': 0, 'intent': 'general'}

        cache_key = self._result_cache_key(question)
        if self.query_cache_ttl > 0 and (not stream or self.answer_mode == 'extractive'):
            cached_result = cache.get(cache_key)
            if cached_result:
                cached_answer = str(cached_result.get('answer', ''))
                if self._is_abstention_answer(cached_answer):
                    cache.delete(cache_key)
                else:
                    logger.info('RAG cache hit for tenant %s', self.tenant.id)
                    if stream:
                        answer_state = StreamAnswerState(tokens=[cached_answer], final_answer=cached_answer)

                        def _cached_single_chunk():
                            yield cached_answer

                        streamed_result = dict(cached_result)
                        streamed_result['answer'] = _cached_single_chunk()
                        streamed_result['answer_state'] = answer_state
                        return streamed_result
                    return cached_result

        t0 = time.perf_counter()
        intent = self.detect_intent(question)

        t_retrieve_start = time.perf_counter()
        if self.enable_agentic_rag:
            chunks, context = self._agentic_retrieve_context(question, intent)
        else:
            chunks = self.retrieve(question, k=self.retrieval_k)
            chunks = self.rerank(question, chunks)
            context = self.build_hierarchical_context(intent, chunks, question)
        t_retrieve = time.perf_counter() - t_retrieve_start

        if not context:
            return {'answer': self._no_info_message(question), 'sources': [], 'chunks_used': 0, 'intent': intent}

        context_sufficient = True
        if self.enable_agentic_rag:
            context_sufficient = self._is_context_sufficient(chunks, context, intent=intent)
            if not context_sufficient:
                signals = self._context_quality_signals(chunks, context)
                logger.info(
                    'Agentic retrieval below threshold; continuing with best available context '
                    'tenant=%s chunks=%d top_score=%.3f top_overlap=%.3f',
                    self.tenant.id,
                    len(chunks),
                    signals['top_score'],
                    signals['top_overlap'],
                )

        answer_state = None
        if stream:
            if self.answer_mode == 'extractive':
                if (
                    self.enable_agentic_rag
                    and self.extractive_require_context_sufficient
                    and self._is_low_confidence_for_extractive(chunks, context, intent)
                ):
                    extracted = self._no_info_message(question)
                else:
                    extracted = self._extractive_fallback_answer(question, context)
                    if not self._is_abstention_answer(extracted):
                        if self.extractive_enforce_query_language:
                            extracted = self._ensure_query_language(
                                question,
                                extracted,
                                allow_llm_rewrite=self.extractive_use_llm_rewrite,
                            )
                        extracted = self._postprocess_answer(question, extracted, context=context) or extracted
                if self._is_abstention_answer(extracted):
                    extracted = self._no_info_message(question)
                answer_state = StreamAnswerState(tokens=[extracted], final_answer=extracted)

                def _single_chunk():
                    yield extracted

                answer = _single_chunk()
            else:
                answer_state = StreamAnswerState()
                answer = self.generate_stream(question, context, state=answer_state)
        else:
            if self.answer_mode == 'extractive':
                if (
                    self.enable_agentic_rag
                    and self.extractive_require_context_sufficient
                    and self._is_low_confidence_for_extractive(chunks, context, intent)
                ):
                    answer = self._no_info_message(question)
                else:
                    answer = self._extractive_fallback_answer(question, context)
                    if not self._is_abstention_answer(answer):
                        if self.extractive_enforce_query_language:
                            answer = self._ensure_query_language(
                                question,
                                answer,
                                allow_llm_rewrite=self.extractive_use_llm_rewrite,
                            )
                        answer = self._postprocess_answer(question, answer, context=context) or answer
                if self._is_abstention_answer(answer):
                    answer = self._no_info_message(question)
            else:
                answer = self.generate(question, context)
                lexical_grounded, lexical_reason = self._lexical_grounding_check(question, answer, context, intent)
                if not lexical_grounded:
                    logger.warning('Lexical grounding failed tenant=%s reason=%s', self.tenant.id, lexical_reason)
                    answer = self._extractive_fallback_answer(question, context)
                    if self._is_abstention_answer(answer):
                        answer = self._no_info_message(question)

                if self.answer_mode != 'hybrid':
                    grounded, reason = self._self_check_answer_grounding(question, context, answer)
                    if not grounded:
                        logger.warning('Agentic self-check failed tenant=%s reason=%s', self.tenant.id, reason)
                        answer = self._extractive_fallback_answer(question, context)
                        if self._is_abstention_answer(answer):
                            answer = self._no_info_message(question)

        seen_sources = set()
        unique_sources = []
        for chunk in chunks:
            source = chunk.get('metadata', {}).get('source')
            if source and source not in seen_sources:
                seen_sources.add(source)
                unique_sources.append(
                    {
                        'document_id': chunk.get('metadata', {}).get('document_id'),
                        'source': source,
                        'page': chunk.get('metadata', {}).get('page'),
                        'score': round(chunk.get('final_score', 0), 3),
                        'overlap': chunk.get('lexical_overlap', 0.0),
                    }
                )

        total_time = time.perf_counter() - t0
        logger.info('RAG query done in %.2fs (retrieve %.2fs) tenant=%s', total_time, t_retrieve, self.tenant.id)

        result = {'answer': answer, 'sources': unique_sources, 'chunks_used': len(chunks), 'intent': intent}
        if stream:
            result['answer_state'] = answer_state

        if self.query_cache_ttl > 0 and (not stream or self.answer_mode == 'extractive'):
            if stream:
                answer_text = str(getattr(answer_state, 'final_answer', '') or '')
            else:
                answer_text = str(result.get('answer', ''))
            if self._is_abstention_answer(answer_text):
                logger.info('Skipping cache for abstention answer tenant=%s', self.tenant.id)
            else:
                cache_payload = dict(result)
                cache_payload['answer'] = answer_text
                cache_payload.pop('answer_state', None)
                cache.set(cache_key, cache_payload, timeout=self.query_cache_ttl)

        return result











