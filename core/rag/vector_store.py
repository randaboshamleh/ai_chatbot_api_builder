import logging
from typing import List, Dict, Any

try:
    import chromadb
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    chromadb = None

from core.rag.embeddings import OllamaEmbeddingEngine

logger = logging.getLogger(__name__)


class TenantVectorStore:

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.collection_name = f"tenant_{tenant_id.replace('-', '')}"
        self.embedding_engine = OllamaEmbeddingEngine()

        if not CHROMADB_AVAILABLE:
            logger.warning("ChromaDB not available. Vector operations will be disabled.")
            return

        try:
            from django.conf import settings
            import os
            
            # Use environment variables directly to avoid localhost issue
            chroma_host = os.getenv('CHROMA_HOST', getattr(settings, 'CHROMA_HOST', 'chromadb'))
            chroma_port = int(os.getenv('CHROMA_PORT', getattr(settings, 'CHROMA_PORT', 8000)))
            
            self.client = chromadb.HttpClient(
                host=chroma_host,
                port=chroma_port,
            )

            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"tenant_id": tenant_id},
            )
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            self.client = None
            self.collection = None

    def add_documents(self, chunks: List[Any], document_id: str) -> List[str]:
        if not CHROMADB_AVAILABLE or not self.collection:
            logger.warning("ChromaDB not available for add_documents")
            return []

        texts = [chunk.page_content for chunk in chunks]
        embeddings = self.embedding_engine.embed_documents(texts)
        ids = [f"{document_id}_{i}" for i in range(len(chunks))]

        metadatas = []
        for chunk in chunks:
            meta = {**chunk.metadata, 'document_id': document_id}
            for key, value in meta.items():
                if isinstance(value, list):
                    meta[key] = ', '.join(str(v) for v in value)
                elif isinstance(value, dict):
                    meta[key] = str(value)
            metadatas.append(meta)

        try:
            self.collection.upsert(
                ids=ids,
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
            )
            return ids
        except Exception as e:
            logger.error(f"Failed to add documents to ChromaDB: {e}")
            return []

    def similarity_search(self, query: str, k: int = 5) -> List[Dict]:
        if not CHROMADB_AVAILABLE or not self.collection:
            logger.warning("ChromaDB not available for similarity_search")
            return []

        try:
            query_embedding = self.embedding_engine.embed_query(query)
            
            # Check collection count first
            count = self.collection.count()
            if count == 0:
                logger.warning(f"Collection {self.collection_name} is empty")
                return []
            
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=min(k, count),
            )

            chunks = []
            if results.get('documents') and results['documents'][0]:
                for doc, meta, dist in zip(
                    results['documents'][0],
                    results['metadatas'][0],
                    results['distances'][0],
                ):
                    similarity = 1 / (1 + dist)
                    chunks.append({
                        'content': doc,
                        'metadata': meta,
                        'similarity_score': similarity,
                    })

            return chunks
        except Exception as e:
            logger.error(f"Similarity search failed: {e}")
            return []

    def keyword_search(self, query: str, k: int = 5) -> List[Dict]:
        if not CHROMADB_AVAILABLE or not self.collection:
            logger.warning("ChromaDB not available for keyword_search")
            return []

        try:
            # Get all documents and filter manually (ChromaDB 0.5.23 doesn't support $contains well)
            all_results = self.collection.get()
            
            chunks = []
            if all_results.get('documents'):
                query_lower = query.lower()
                for doc, meta in zip(all_results['documents'], all_results['metadatas']):
                    if query_lower in doc.lower():
                        chunks.append({
                            'content': doc,
                            'metadata': meta,
                            'similarity_score': 0.5,
                        })
                        if len(chunks) >= k:
                            break
            return chunks
        except Exception as e:
            logger.warning(f"Keyword search failed: {e}")
            return []

    def delete_document(self, document_id: str):
        if not CHROMADB_AVAILABLE or not self.collection:
            logger.warning("ChromaDB not available for delete_document")
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
