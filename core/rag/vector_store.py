import logging
import re
import warnings
from typing import List, Dict, Any

CHROMADB_IMPORT_ERROR = None

warnings.filterwarnings(
    "ignore",
    message="Core Pydantic V1 functionality isn't compatible with Python 3.14 or greater.",
    module="chromadb.config",
)

try:
    import chromadb
    CHROMADB_AVAILABLE = True
except Exception as exc:
    CHROMADB_AVAILABLE = False
    chromadb = None
    CHROMADB_IMPORT_ERROR = exc

from core.rag.embeddings import OllamaEmbeddingEngine

logger = logging.getLogger(__name__)
KEYWORD_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+|[\u0600-\u06FF]+")

# Special document_id prefix for summaries
SUMMARY_DOC_PREFIX = "__summary__"


class TenantVectorStore:
    _import_error_logged = False

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.collection_name = f"tenant_{tenant_id.replace('-', '')}"
        self.embedding_engine = OllamaEmbeddingEngine()
        self.client = None
        self.collection = None

        if not CHROMADB_AVAILABLE:
            if not TenantVectorStore._import_error_logged:
                logger.warning(
                    "ChromaDB disabled because import failed: %s. "
                    "Use Python 3.13 or lower for current dependency set.",
                    CHROMADB_IMPORT_ERROR,
                )
                TenantVectorStore._import_error_logged = True
            return

        try:
            from django.conf import settings
            import os

            chroma_host = os.getenv('CHROMA_HOST', getattr(settings, 'CHROMA_HOST', 'chromadb'))
            chroma_port = int(os.getenv('CHROMA_PORT', getattr(settings, 'CHROMA_PORT', 8000)))

            self.client = chromadb.HttpClient(host=chroma_host, port=chroma_port)

            try:
                existing = self.client.get_collection(name=self.collection_name)
                meta = existing.metadata or {}
                if meta.get("hnsw:space") != "cosine":
                    logger.warning(f"Collection {self.collection_name} uses L2, recreating with cosine...")
                    self.client.delete_collection(name=self.collection_name)
                    raise ValueError("recreate")
                self.collection = existing
            except Exception as e:
                if "does not exist" in str(e) or "recreate" in str(e):
                    self.collection = self.client.create_collection(
                        name=self.collection_name,
                        metadata={"tenant_id": tenant_id, "hnsw:space": "cosine"},
                    )
                else:
                    raise
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            self.client = None
            self.collection = None

    def add_documents(self, chunks: List[Any], document_id: str) -> List[str]:
        if not CHROMADB_AVAILABLE or not self.collection:
            return []

        texts = [chunk.page_content for chunk in chunks]
        embeddings = self.embedding_engine.embed_documents(texts)
        ids = [f"{document_id}_{i}" for i in range(len(chunks))]

        metadatas = []
        for chunk in chunks:
            meta = {**chunk.metadata, 'document_id': document_id, 'is_summary': 'false'}
            for key, value in meta.items():
                if isinstance(value, list):
                    meta[key] = ', '.join(str(v) for v in value)
                elif isinstance(value, dict):
                    meta[key] = str(value)
            metadatas.append(meta)

        try:
            self.collection.upsert(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)
            return ids
        except Exception as e:
            logger.error(f"Failed to add documents: {e}")
            return []

    def _db_fallback_search(self, query: str, k: int = 5) -> List[Dict]:
        """
        Fallback retrieval when ChromaDB is unavailable.
        Uses indexed DocumentChunk rows for the current tenant with token-hit scoring.
        """
        try:
            from django.db.models import Q
            from apps.documents.models import DocumentChunk
        except Exception as exc:
            logger.warning("DB fallback retrieval unavailable: %s", exc)
            return []

        query_norm = (query or "").strip().lower()
        if not query_norm:
            return []

        tokens = [tok for tok in KEYWORD_TOKEN_RE.findall(query_norm) if len(tok) >= 2]
        token_terms = list(dict.fromkeys(tokens))[:8]

        qs = DocumentChunk.objects.filter(
            document__tenant_id=self.tenant_id,
            document__status='indexed',
        )

        lookup_q = Q()
        for tok in token_terms[:5]:
            lookup_q |= Q(content__icontains=tok)

        # Try phrase hit first; fallback to token OR query if phrase is too strict.
        phrase_q = Q(content__icontains=query_norm)
        if phrase_q:
            scoped = qs.filter(phrase_q)
            if not scoped.exists() and lookup_q:
                scoped = qs.filter(lookup_q)
        else:
            scoped = qs.filter(lookup_q) if lookup_q else qs

        rows = scoped.values('content', 'metadata')[: max(120, k * 40)]
        if not rows:
            return []

        scored: List[Dict] = []
        seen = set()
        for row in rows:
            content = (row.get('content') or "").strip()
            if not content:
                continue

            content_l = content.lower()
            token_hits = sum(1 for tok in token_terms if tok in content_l)
            phrase_hit = 1 if query_norm in content_l else 0
            if token_hits == 0 and phrase_hit == 0:
                continue

            key = content_l[:400]
            if key in seen:
                continue
            seen.add(key)

            score = min(0.9, 0.46 + (token_hits * 0.06) + (0.16 if phrase_hit else 0.0))
            scored.append(
                {
                    'content': content,
                    'metadata': row.get('metadata') or {},
                    'similarity_score': round(score, 4),
                }
            )

        scored.sort(key=lambda item: item.get('similarity_score', 0.0), reverse=True)
        return scored[:k]

    def add_summaries(self, summaries: List[Dict]) -> None:
        """
        Store generated summaries as special chunks.
        Each summary dict: {text, level, category, document_id (optional)}
        level: 'global_summary' | 'section_summary'
        """
        if not CHROMADB_AVAILABLE or not self.collection:
            return

        texts = [s['text'] for s in summaries]
        if not texts:
            return

        embeddings = self.embedding_engine.embed_documents(texts)
        ids = []
        metadatas = []

        for i, s in enumerate(summaries):
            level = s.get('level', 'section_summary')
            category = s.get('category', 'general')
            doc_id = s.get('document_id', 'all')
            uid = f"{SUMMARY_DOC_PREFIX}{level}_{category}_{doc_id}"
            ids.append(uid)
            metadatas.append({
                'level': level,
                'category': category,
                'document_id': doc_id,
                'is_summary': 'true',
            })

        try:
            self.collection.upsert(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)
            logger.info(f"Stored {len(summaries)} summaries for tenant {self.tenant_id}")
        except Exception as e:
            logger.error(f"Failed to store summaries: {e}")

    def get_summaries(self, level: str = None, category: str = None) -> List[Dict]:
        """Retrieve stored summaries, optionally filtered by level and/or category."""
        if not CHROMADB_AVAILABLE or not self.collection:
            return []

        try:
            conditions = [{"is_summary": {"$eq": "true"}}]
            if level:
                conditions.append({"level": {"$eq": level}})
            if category:
                conditions.append({"category": {"$eq": category}})

            if len(conditions) == 1:
                where = conditions[0]
            else:
                where = {"$and": conditions}

            results = self.collection.get(where=where)
            summaries = []
            if results.get('documents'):
                for doc, meta in zip(results['documents'], results['metadatas']):
                    summaries.append({'text': doc, 'metadata': meta})
            return summaries
        except Exception as e:
            logger.warning(f"get_summaries failed: {e}")
            return []

    def similarity_search(self, query: str, k: int = 5) -> List[Dict]:
        if not CHROMADB_AVAILABLE or not self.collection:
            return self._db_fallback_search(query, k=k)

        try:
            query_embedding = self.embedding_engine.embed_query(query)
            count = self.collection.count()
            if count == 0:
                return []

            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=min(k, count),
                where={"is_summary": {"$eq": "false"}},
            )

            chunks = []
            if results.get('documents') and results['documents'][0]:
                for doc, meta, dist in zip(
                    results['documents'][0],
                    results['metadatas'][0],
                    results['distances'][0],
                ):
                    similarity = max(0.0, 1.0 - (dist / 2.0))
                    chunks.append({'content': doc, 'metadata': meta, 'similarity_score': similarity})
            return chunks
        except Exception as e:
            logger.error(f"Similarity search failed: {e}")
            return []

    def keyword_search(self, query: str, k: int = 5) -> List[Dict]:
        if not CHROMADB_AVAILABLE or not self.collection:
            return self._db_fallback_search(query, k=k)

        try:
            query_norm = (query or "").strip().lower()
            if not query_norm:
                return []

            query_tokens = [tok for tok in KEYWORD_TOKEN_RE.findall(query_norm) if len(tok) >= 2]
            # Keep unique order and avoid scanning too many terms.
            token_terms = list(dict.fromkeys(query_tokens))[:8]

            # Prefer server-side document filtering to avoid fetching the entire corpus.
            try:
                exact_results = self.collection.get(
                    where={"is_summary": {"$eq": "false"}},
                    where_document={"$contains": query_norm},
                    limit=k,
                )
                chunks = []
                if exact_results.get("documents"):
                    for doc, meta in zip(exact_results["documents"], exact_results["metadatas"]):
                        chunks.append({"content": doc, "metadata": meta, "similarity_score": 0.72})
                if len(chunks) >= k:
                    return chunks[:k]
            except Exception:
                pass

            # Fallback: bounded scan with token-hit scoring.
            max_scan = max(120, k * 40)
            all_results = self.collection.get(
                where={"is_summary": {"$eq": "false"}},
                limit=max_scan,
            )
            if not all_results.get("documents"):
                return []

            scored_chunks = []
            for doc, meta in zip(all_results["documents"], all_results["metadatas"]):
                text_lower = doc.lower()
                token_hits = sum(1 for tok in token_terms if tok in text_lower)
                full_query_hit = 1 if query_norm in text_lower else 0

                if token_hits == 0 and full_query_hit == 0:
                    continue

                score = min(0.86, 0.42 + (token_hits * 0.06) + (0.18 if full_query_hit else 0.0))
                scored_chunks.append(
                    {"content": doc, "metadata": meta, "similarity_score": round(score, 4)}
                )

            scored_chunks.sort(key=lambda item: item.get("similarity_score", 0.0), reverse=True)
            return scored_chunks[:k]
        except Exception as e:
            logger.warning(f"Keyword search failed: {e}")
            return []

    def delete_document(self, document_id: str):
        if not CHROMADB_AVAILABLE or not self.collection:
            return

        try:
            results = self.collection.get(
                where={"document_id": {"$eq": document_id}},
                include=[],
            )
            ids_to_delete = results.get('ids', [])
            if ids_to_delete:
                self.collection.delete(ids=ids_to_delete)
                logger.info(f"Deleted {len(ids_to_delete)} chunks for document {document_id}")
        except Exception as e:
            logger.warning(f"Could not delete from ChromaDB: {e}")
