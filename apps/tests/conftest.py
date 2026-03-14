"""
conftest.py - Mock heavy optional dependencies before Django test collection.
This prevents ImportError for chromadb, langchain, sentence-transformers, etc.
which are not installed in the CI environment.
"""
import sys
from unittest.mock import MagicMock

# ── Packages that are NOT installed in CI (heavy ML/vector deps) ──────────────
MOCK_MODULES = [
    "chromadb",
    "chromadb.config",
    "sentence_transformers",
    "langchain",
    "langchain.text_splitter",
    "langchain_text_splitters",
    "langchain_community",
    "langchain_community.document_loaders",
    "langchain_core",
    "langchain_core.documents",
    "whisper",
    "torch",
    "PIL",
    "unstructured",
]

for mod in MOCK_MODULES:
    if mod not in sys.modules:
        sys.modules[mod] = MagicMock()
