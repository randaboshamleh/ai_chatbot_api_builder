import logging
import hashlib
from typing import List, Dict, Any


try:
    import ollama
    from django.conf import settings
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    ollama = None

from core.rag.vector_store import TenantVectorStore

logger = logging.getLogger(__name__)


RAG_PROMPT_TEMPLATE = """
You are a specialized AI assistant for the company.

CRITICAL INSTRUCTIONS:
- Answer ONLY based on the provided context
- If you don't find the answer, say: "I don't have enough information about this topic."
- DO NOT invent or make up information
- **YOU MUST respond in the EXACT SAME LANGUAGE as the question:**
  * If the question is in Arabic, respond ENTIRELY in Arabic
  * If the question is in English, respond ENTIRELY in English
  * Match the language of the question precisely

Context:
{context}

Question:
{question}

Answer (in the same language as the question):
"""


class RAGPipeline:

    def __init__(self, tenant):
        self.tenant = tenant
        self.vector_store = TenantVectorStore(str(tenant.id))

        if not OLLAMA_AVAILABLE:
            logger.warning("Ollama not available. LLM operations will be disabled.")
            self.llm_client = None
            self.model = None
        else:
            try:
                from django.conf import settings
                import os
                
                # Use environment variables directly to avoid localhost issue
                ollama_host = os.getenv('OLLAMA_BASE_URL', getattr(settings, 'OLLAMA_BASE_URL', 'http://ollama:11434'))
                
                self.llm_client = ollama.Client(host=ollama_host)
                self.model = settings.OLLAMA_MODEL
            except Exception as e:
                logger.error(f"Failed to initialize Ollama client: {e}")
                self.llm_client = None
                self.model = None

       
        self.cache: Dict[str, Dict] = {}

    def _cache_key(self, query: str):
        return hashlib.md5(query.encode()).hexdigest()

    def retrieve(self, query: str, k: int = 4) -> List[Dict]:  
        try:
            semantic_results = self.vector_store.similarity_search(query, k=k)
        except Exception:
            semantic_results = []

        try:
            keyword_results = self.vector_store.keyword_search(query, k=k)
        except Exception:
            keyword_results = []

        combined = semantic_results + keyword_results

        seen = set()
        unique = []

        for r in combined:
            content = r.get("content")
            if content and content not in seen:
                seen.add(content)
                unique.append(r)

        return unique

    def rerank(self, query: str, chunks: List[Dict]) -> List[Dict]:
        for chunk in chunks:
            score = chunk.get("similarity_score", 0)
            if query.lower() in chunk.get("content", "").lower():
                score += 0.2
            chunk["final_score"] = score

        chunks.sort(key=lambda x: x["final_score"], reverse=True)
        return chunks[:2]  

    def build_context(self, chunks: List[Dict]) -> str:
        if not chunks:
            return ""

        parts = []
        for i, chunk in enumerate(chunks):
            source = chunk.get("metadata", {}).get("source", "")
            page = chunk.get("metadata", {}).get("page", "")
            text = chunk.get("content", "")[:600]  
            parts.append(f"[Source {i+1}: {source} page {page}]\n{text}")

        context = "\n\n---\n\n".join(parts)
        return context[:2000]  

    def generate(self, query: str, context: str) -> str:
        if not OLLAMA_AVAILABLE or not self.llm_client:
            return "Sorry, the AI service is currently unavailable."

        prompt = RAG_PROMPT_TEMPLATE.format(context=context, question=query)

        try:
            response = self.llm_client.generate(
                model=self.model,
                prompt=prompt,
                options={
                    "temperature": 0.1,
                    "num_predict": 200, 
                    "top_p": 0.9,
                },
            )
            return response["response"]
        except Exception as e:
            logger.error(f"Failed to generate response: {e}")
            return "Sorry, an error occurred while generating the response."

    def generate_stream(self, query: str, context: str):
        """Generate a streaming response"""
        if not OLLAMA_AVAILABLE or not self.llm_client:
            yield "Sorry, the AI service is currently unavailable."
            return

        prompt = RAG_PROMPT_TEMPLATE.format(context=context, question=query)

        try:
            response = self.llm_client.generate(
                model=self.model,
                prompt=prompt,
                stream=True,
                options={
                    "temperature": 0.1,
                    "num_predict": 200,  
                    "top_p": 0.9,
                },
            )

            for chunk in response:
                if chunk.get('response'):
                    yield chunk['response']
        except Exception as e:
            logger.error(f"Failed to generate streaming response: {e}")
            yield "Sorry, an error occurred while generating the response."

    def query(self, question: str, stream: bool = False) -> Dict[str, Any]:
        cache_key = self._cache_key(question)

        if not stream and cache_key in self.cache:
            logger.info("Cache hit")
            return self.cache[cache_key]

        chunks = self.retrieve(question)

        chunks = self.rerank(question, chunks)

        context = self.build_context(chunks)

        if not context:
            result = {
                "answer": "I don't have enough information about this topic in the available documents.",
                "sources": [],
                "chunks_used": 0,
            }
            return result

     
        if stream:
            answer = self.generate_stream(question, context)
        else:
            answer = self.generate(question, context)

        result = {
            "answer": answer,
            "sources": [
                {
                    "document_id": c.get("metadata", {}).get("document_id"),
                    "source": c.get("metadata", {}).get("source"),
                    "page": c.get("metadata", {}).get("page"),
                    "score": round(c.get("final_score", 0), 3),
                }
                for c in chunks
            ],
            "chunks_used": len(chunks),
        }

       
        if not stream:
            self.cache[cache_key] = result

        return result