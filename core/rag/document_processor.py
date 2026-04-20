import hashlib
import time
import logging
import re
from typing import List, Dict, Any, Tuple

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    PyPDFLoader,
    Docx2txtLoader,
    TextLoader,
    CSVLoader,
)
from langchain_core.documents import Document as LangchainDocument

logger = logging.getLogger(__name__)

# ── Category keyword mapping ──────────────────────────────────────────────────
CATEGORY_KEYWORDS = {
    "pricing": [
        "price", "pricing", "cost", "plan", "plans", "subscription", "fee", "fees",
        "payment", "billing", "invoice", "discount", "offer", "package", "tier",
        "سعر", "أسعار", "تكلفة", "خطة", "خطط", "اشتراك", "رسوم", "دفع", "فاتورة",
    ],
    "features": [
        "feature", "features", "integration", "integrations", "dashboard", "api",
        "capability", "capabilities", "function", "functionality", "tool", "tools",
        "ميزة", "ميزات", "تكامل", "لوحة", "وظيفة", "أداة",
    ],
    "support": [
        "support", "help", "contact", "faq", "issue", "problem", "error", "bug",
        "troubleshoot", "guide", "how to", "tutorial", "documentation",
        "دعم", "مساعدة", "تواصل", "مشكلة", "خطأ", "دليل", "كيف",
    ],
    "onboarding": [
        "start", "setup", "install", "configure", "begin", "getting started",
        "register", "signup", "sign up", "create account", "onboard",
        "بدء", "إعداد", "تثبيت", "تسجيل", "حساب",
    ],
}

# Patterns that indicate a section heading in plain text / PDF extracted text
_HEADING_RE = re.compile(
    r'^(?:'
    r'\d+[\.\)]\s+[A-Z\u0600-\u06FF]'   # "1. Title" or "1) Title"
    r'|#{1,4}\s+'                          # Markdown ## headings
    r'|[A-Z][A-Z\s]{4,}$'                 # ALL CAPS line (≥5 chars)
    r'|(?:Chapter|Section|Part|الفصل|القسم|الجزء)\s'  # explicit section words
    r')',
    re.MULTILINE,
)

MAX_CHUNK_SIZE = 1200   # hard cap after semantic split
CHUNK_OVERLAP  = 150


def tag_category(text: str) -> str:
    """Assign a category to a chunk based on keyword matching."""
    text_lower = text.lower()
    scores = {cat: 0 for cat in CATEGORY_KEYWORDS}
    for cat, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                scores[cat] += 1
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "general"


def _semantic_split(text: str) -> List[str]:
    """
    Split text into semantic sections by detecting headings.
    Each section = one logical topic.
    Falls back to paragraph splitting when no headings found.
    """
    lines = text.splitlines()
    sections: List[str] = []
    current: List[str] = []

    for line in lines:
        if _HEADING_RE.match(line.strip()) and current:
            block = "\n".join(current).strip()
            if block:
                sections.append(block)
            current = [line]
        else:
            current.append(line)

    if current:
        block = "\n".join(current).strip()
        if block:
            sections.append(block)

    # If no headings found, fall back to double-newline paragraph split
    if len(sections) <= 1:
        sections = [s.strip() for s in re.split(r'\n{2,}', text) if s.strip()]

    return sections if sections else [text]


class DocumentProcessor:
    """
    Document processor: load → semantic chunk → tag → prepare for embedding.

    Strategy (2-pass):
      Pass 1 – split by headings / paragraphs (semantic boundaries)
      Pass 2 – if a section > MAX_CHUNK_SIZE, sub-split with RecursiveCharacterTextSplitter
    """

    LOADER_MAPPING = {
        'application/pdf': PyPDFLoader,
        'application/msword': Docx2txtLoader,
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': Docx2txtLoader,
        'application/vnd.ms-excel': None,
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': None,
        'text/plain': TextLoader,
        'text/csv': CSVLoader,
    }

    def __init__(self, chunk_size: int = MAX_CHUNK_SIZE, chunk_overlap: int = CHUNK_OVERLAP):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        # Used only as fallback for oversized sections
        self._fallback_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", "! ", "? ", ", ", " ", ""],
        )

    def load_document(self, file_path: str, file_type: str) -> List[LangchainDocument]:
        loader_class = self.LOADER_MAPPING.get(file_type)
        if not loader_class:
            raise ValueError(f"Unsupported file type: {file_type}")
        loader = loader_class(file_path)
        documents = loader.load()
        logger.info(f"Loaded {len(documents)} pages from {file_path}")
        return documents

    def _pages_to_sections(self, documents: List[LangchainDocument]) -> List[Dict]:
        """
        Merge all page texts, then split semantically.
        Returns list of {text, page_hint} dicts.
        """
        # Build a map: char_offset → page number
        full_text = ""
        page_offsets: List[Tuple[int, int]] = []  # (start_char, page_num)
        for doc in documents:
            page_offsets.append((len(full_text), doc.metadata.get("page", 0)))
            full_text += doc.page_content + "\n\n"

        def char_to_page(pos: int) -> int:
            page = 0
            for start, pg in page_offsets:
                if pos >= start:
                    page = pg
                else:
                    break
            return page

        raw_sections = _semantic_split(full_text)
        result = []
        offset = 0
        for sec in raw_sections:
            idx = full_text.find(sec, offset)
            page_hint = char_to_page(idx) if idx != -1 else 0
            offset = idx + len(sec) if idx != -1 else offset
            result.append({"text": sec, "page": page_hint})
        return result

    def split_documents(
        self,
        documents: List[LangchainDocument],
        metadata: Dict[str, Any] = None,
    ) -> List[LangchainDocument]:
        """
        2-pass semantic chunking:
          1. Split by headings/paragraphs
          2. Sub-split oversized sections
        """
        sections = self._pages_to_sections(documents)
        chunks: List[LangchainDocument] = []

        for sec in sections:
            text = sec["text"]
            page = sec["page"]

            if len(text) <= self.chunk_size:
                # Section fits → keep as one chunk
                chunks.append(LangchainDocument(
                    page_content=text,
                    metadata={"page": page},
                ))
            else:
                # Section too large → sub-split
                sub_docs = self._fallback_splitter.create_documents(
                    [text], metadatas=[{"page": page}]
                )
                chunks.extend(sub_docs)

        # Tag each chunk with category + index
        for i, chunk in enumerate(chunks):
            category = tag_category(chunk.page_content)
            chunk.metadata.update({
                "chunk_index": i,
                "total_chunks": len(chunks),
                "category": category,
                "level": "detail",
                "is_summary": "false",
                **(metadata or {}),
            })

        logger.info(f"Semantic split → {len(chunks)} chunks (from {len(sections)} sections)")
        return chunks

    def process(
        self,
        file_path: str,
        file_type: str,
        metadata: Dict[str, Any] = None,
    ) -> Tuple[List[LangchainDocument], float]:
        start_time = time.time()
        documents = self.load_document(file_path, file_type)
        chunks = self.split_documents(documents, metadata)
        processing_time = time.time() - start_time
        logger.info(f"Document processed in {processing_time:.2f}s")
        return chunks, processing_time

    def get_full_text(self, chunks: List[LangchainDocument]) -> str:
        return "\n\n".join(c.page_content for c in chunks)

    def get_category_texts(self, chunks: List[LangchainDocument]) -> Dict[str, str]:
        groups: Dict[str, List[str]] = {}
        for chunk in chunks:
            cat = chunk.metadata.get("category", "general")
            groups.setdefault(cat, []).append(chunk.page_content)
        return {cat: "\n\n".join(texts) for cat, texts in groups.items()}

    @staticmethod
    def compute_checksum(file_path: str) -> str:
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        return sha256.hexdigest()
