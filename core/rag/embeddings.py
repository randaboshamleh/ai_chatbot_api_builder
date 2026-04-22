import logging
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
    توليد Embeddings باستخدام Ollama محلياً
    يضمن خصوصية البيانات لأن كل شيء يعمل on-premise
    """

    def __init__(self):
        if not OLLAMA_AVAILABLE:
            logger.warning("Ollama not available. Embedding operations will be disabled.")
            return

        try:
            from django.conf import settings
            import os
            
            # Use environment variables directly to avoid localhost issue
            ollama_host = os.getenv('OLLAMA_BASE_URL', getattr(settings, 'OLLAMA_BASE_URL', 'http://ollama:11434'))
            
            self.model = settings.OLLAMA_EMBEDDING_MODEL
            self.client = ollama.Client(host=ollama_host)
        except Exception as e:
            logger.error(f"Failed to initialize Ollama client: {e}")
            self.client = None
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """توليد Embeddings لقائمة نصوص"""
        if not OLLAMA_AVAILABLE or not self.client:
            logger.warning("Ollama not available for embed_documents")
            return [[0.0] * 384 for _ in texts]  # dummy embeddings

        embeddings = []
        for text in texts:
            try:
                response = self.client.embeddings(
                    model=self.model,
                    prompt=text,
                )
                embeddings.append(response['embedding'])
            except Exception as e:
                logger.error(f"Failed to generate embedding: {e}")
                embeddings.append([0.0] * 384)  # dummy embedding
        
        return embeddings
    
    def embed_query(self, text: str) -> List[float]:
        """توليد Embedding لسؤال واحد"""
        if not OLLAMA_AVAILABLE or not self.client:
            logger.warning("Ollama not available for embed_query")
            return [0.0] * 384  # dummy embedding

        try:
            response = self.client.embeddings(
                model=self.model,
                prompt=text,
            )
            return response['embedding']
        except Exception as e:
            logger.error(f"Failed to generate query embedding: {e}")
            return [0.0] * 384  # dummy embedding