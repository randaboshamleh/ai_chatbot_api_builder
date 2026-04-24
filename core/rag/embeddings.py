import logging
import os
from concurrent.futures import ThreadPoolExecutor
from typing import List

try:
    import ollama
    from django.conf import settings

    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    ollama = None

logger = logging.getLogger(__name__)


class OllamaEmbeddingEngine:
    """
    Generate embeddings using local Ollama.
    """

    def __init__(self):
        if not OLLAMA_AVAILABLE:
            logger.warning("Ollama not available. Embedding operations will be disabled.")
            return

        try:
            ollama_host = os.getenv('OLLAMA_BASE_URL', getattr(settings, 'OLLAMA_BASE_URL', 'http://ollama:11434'))

            self.model = settings.OLLAMA_EMBEDDING_MODEL
            self.client = ollama.Client(host=ollama_host)
            self.batch_size = max(
                1,
                int(os.getenv('OLLAMA_EMBED_BATCH_SIZE', getattr(settings, 'OLLAMA_EMBED_BATCH_SIZE', 24))),
            )
            self.max_workers = max(
                1,
                int(os.getenv('OLLAMA_EMBED_MAX_WORKERS', getattr(settings, 'OLLAMA_EMBED_MAX_WORKERS', 1))),
            )
            self.max_chars = max(
                200,
                int(os.getenv('OLLAMA_EMBED_MAX_CHARS', getattr(settings, 'OLLAMA_EMBED_MAX_CHARS', 2400))),
            )
        except Exception as e:
            logger.error(f"Failed to initialize Ollama client: {e}")
            self.client = None

    def _normalize_text(self, text: str) -> str:
        text = (text or '').replace('\x00', '').strip()
        return text[: self.max_chars]

    def _embed_single(self, text: str) -> List[float]:
        normalized = self._normalize_text(text)
        if not normalized:
            return [0.0] * 384

        try:
            response = self.client.embeddings(
                model=self.model,
                prompt=normalized,
            )
            return response['embedding']
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return [0.0] * 384

    @staticmethod
    def _chunked(items: List[str], size: int):
        for i in range(0, len(items), size):
            yield items[i:i + size]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts."""
        if not OLLAMA_AVAILABLE or not self.client:
            logger.warning("Ollama not available for embed_documents")
            return [[0.0] * 384 for _ in texts]

        if not texts:
            return []

        normalized_texts = [self._normalize_text(t) for t in texts]

        # Fast path: newer Ollama client supports batched `embed`.
        if hasattr(self.client, 'embed'):
            embeddings: List[List[float]] = []
            for batch in self._chunked(normalized_texts, self.batch_size):
                try:
                    response = self.client.embed(
                        model=self.model,
                        input=batch,
                    )
                    batch_embeddings = response.get('embeddings', [])
                    if len(batch_embeddings) == len(batch):
                        embeddings.extend(batch_embeddings)
                        continue
                    logger.warning("Batched embed returned unexpected length; falling back per-item for this batch.")
                except Exception as e:
                    logger.warning(f"Batched embed failed, falling back per-item: {e}")

                embeddings.extend([self._embed_single(text) for text in batch])
            return embeddings

        # Fallback path for older clients.
        if self.max_workers > 1 and len(normalized_texts) > 1:
            with ThreadPoolExecutor(max_workers=min(self.max_workers, len(normalized_texts))) as executor:
                return list(executor.map(self._embed_single, normalized_texts))

        return [self._embed_single(text) for text in normalized_texts]

    def embed_query(self, text: str) -> List[float]:
        """Generate embedding for one query."""
        if not OLLAMA_AVAILABLE or not self.client:
            logger.warning("Ollama not available for embed_query")
            return [0.0] * 384

        return self._embed_single(text)