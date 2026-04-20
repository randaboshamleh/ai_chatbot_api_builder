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

RAG_PROMPT_TEMPLATE = """You are Assistify AI, a professional customer support assistant designed for SaaS businesses.
Your role is to answer customer questions accurately using ONLY the provided company documents and knowledge base.

## Core Behavior:
- Always provide clear, concise, and helpful answers.
- Maintain a professional, friendly, and confident tone.
- Act like a real support agent, not an AI.

## Knowledge Rules:
- Only use the provided context (documents, FAQs, data).
- Do NOT make up information.
- If the answer is not available in the context, respond ONLY with the exact phrase: NO_INFO

## Response Style:
- Keep answers short and direct.
- Use simple, easy-to-understand language.
- When appropriate, format answers with bullet points.
- Avoid long paragraphs unless necessary.

## Language Rules:
- YOU MUST respond in the EXACT SAME LANGUAGE as the question.
- If the question is in Arabic: respond fully in Arabic, keeping technical terms in English in parentheses.
- If the question is in English: respond in English only.
- Do NOT mix languages mid-word.

## Important:
- Never mention AI model, training data, or technical details.
- Always represent the company professionally.
- Do NOT repeat or restate the question.
- Start your answer directly.

Context:
{context}

Question: {question}

Answer:"""

SUMMARY_PROMPT = """Summarize the following text in 2-3 concise sentences. Focus on the key information only.

Text:
{text}

Summary:"""

MIN_RELEVANCE_SCORE = 0.50

INTENT_KEYWORDS = {
    "pricing": ["price", "pricing", "cost", "plan", "plans", "subscription", "fee", "payment",
                "billing", "discount", "package", "tier", "سعر", "أسعار", "تكلفة", "خطة", "اشتراك"],
    "features": ["feature", "features", "integration", "dashboard", "api", "capability",
                 "function", "tool", "ميزة", "ميزات", "تكامل", "لوحة", "أداة"],
    "support": ["support", "help", "contact", "faq", "issue", "problem", "error", "bug",
                "how to", "guide", "دعم", "مساعدة", "مشكلة", "خطأ", "كيف"],
    "onboarding": ["start", "setup", "install", "configure", "register", "signup",
                   "getting started", "بدء", "إعداد", "تسجيل"],
}


class RAGPipeline:

    def __init__(self, tenant):
        self.tenant = tenant
        self.vector_store = TenantVectorStore(str(tenant.id))

        if not OLLAMA_AVAILABLE:
            logger.warning("Ollama not available.")
            self.llm_client = None
            self.model = None
        else:
            try:
                import os
                ollama_host = os.getenv("OLLAMA_BASE_URL", getattr(settings, "OLLAMA_BASE_URL", "http://ollama:11434"))
                self.llm_client = ollama.Client(host=ollama_host)
                self.model = settings.OLLAMA_MODEL
            except Exception as e:
                logger.error(f"Failed to initialize Ollama client: {e}")
                self.llm_client = None
                self.model = None

        self.cache: Dict[str, Dict] = {}

    def _cache_key(self, query: str) -> str:
        return hashlib.md5(query.encode()).hexdigest()

    def _is_arabic(self, text: str) -> bool:
        arabic_chars = sum(1 for c in text if "\u0600" <= c <= "\u06ff")
        return arabic_chars > len(text) * 0.3

    def _no_info_message(self, question: str) -> str:
        if self._is_arabic(question):
            return "لست متأكدا من ذلك. دعني أوصلك بفريق الدعم لدينا."
        return "I'm not sure about that. Let me connect you with our support team."

    def detect_intent(self, question: str) -> str:
        q_lower = question.lower()
        scores = {cat: 0 for cat in INTENT_KEYWORDS}
        for cat, keywords in INTENT_KEYWORDS.items():
            for kw in keywords:
                if kw in q_lower:
                    scores[cat] += 1
        best = max(scores, key=scores.get)
        intent = best if scores[best] > 0 else "general"
        logger.info(f"Detected intent: {intent}")
        return intent

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
        for c in chunks[:3]:
            logger.info(f"Chunk score={c.get('final_score', 0):.3f} src={c.get('metadata', {}).get('source', '')[:40]}")
        relevant = [c for c in chunks if c.get("final_score", 0) >= MIN_RELEVANCE_SCORE]
        return relevant[:2] if relevant else []

    def build_hierarchical_context(self, intent: str, detail_chunks: List[Dict]) -> str:
        parts = []
        get_summaries = getattr(self.vector_store, "get_summaries", None)

        # Some vector-store backends don't implement hierarchical summaries yet.
        # In that case we gracefully fall back to detail chunks only.
        if callable(get_summaries):
            global_summaries = get_summaries(level="global_summary")
            if global_summaries:
                parts.append("[Overview]\n" + global_summaries[0].get("text", ""))

            if intent != "general":
                section_summaries = get_summaries(level="section_summary", category=intent)
                if section_summaries:
                    parts.append(f"[{intent.capitalize()} Summary]\n" + section_summaries[0].get("text", ""))

        for i, chunk in enumerate(detail_chunks):
            source = chunk.get("metadata", {}).get("source", "")
            page = chunk.get("metadata", {}).get("page", "")
            text = chunk.get("content", "")[:600]
            parts.append(f"[Detail {i+1}: {source} p.{page}]\n{text}")
        context = "\n\n---\n\n".join(parts)
        return context[:2500]

    def _llm_generate(self, prompt: str, max_tokens: int = 200) -> str:
        response = self.llm_client.generate(
            model=self.model,
            prompt=prompt,
            keep_alive="10m",
            options={"temperature": 0.1, "num_predict": max_tokens, "top_p": 0.9, "num_ctx": 1024},
        )
        return response["response"].strip()

    def generate(self, query: str, context: str) -> str:
        if not OLLAMA_AVAILABLE or not self.llm_client:
            return "Sorry, the AI service is currently unavailable."

        prompt = RAG_PROMPT_TEMPLATE.format(context=context, question=query)

        try:
            answer = self._llm_generate(prompt, max_tokens=300)
            if "NO_INFO" in answer or len(answer) < 5:
                return self._no_info_message(query)
            return answer
        except Exception as e:
            logger.error(f"Failed to generate response: {e}")
            return "Sorry, an error occurred while generating the response."

    def generate_stream(self, query: str, context: str):
        if not OLLAMA_AVAILABLE or not self.llm_client:
            yield "Sorry, the AI service is currently unavailable."
            return
        lang_hint = "Arabic" if self._is_arabic(query) else "English"
        prompt = (
            RAG_PROMPT_TEMPLATE.format(context=context, question=query)
            + f"\n[Respond in {lang_hint}. Keep technical terms in English in parentheses if translating.]"
        )
        try:
            response = self.llm_client.generate(
                model=self.model, prompt=prompt, stream=True, keep_alive="10m",
                options={"temperature": 0.1, "num_predict": 300, "top_p": 0.9, "num_ctx": 2048},
            )
            for chunk in response:
                if chunk.get("response"):
                    yield chunk["response"]
        except Exception as e:
            logger.error(f"Streaming failed: {e}")
            yield "Sorry, an error occurred while generating the response."

    def generate_summary(self, text: str, max_chars: int = 3000) -> str:
        if not OLLAMA_AVAILABLE or not self.llm_client:
            return ""
        try:
            prompt = SUMMARY_PROMPT.format(text=text[:max_chars])
            return self._llm_generate(prompt, max_tokens=150)
        except Exception as e:
            logger.error(f"Summary generation failed: {e}")
            return ""

    def query(self, question: str, stream: bool = False) -> Dict[str, Any]:
        cache_key = self._cache_key(question)
        if not stream and cache_key in self.cache:
            logger.info("Cache hit")
            return self.cache[cache_key]
        intent = self.detect_intent(question)
        chunks = self.retrieve(question)
        chunks = self.rerank(question, chunks)
        context = self.build_hierarchical_context(intent, chunks)
        if not context:
            return {"answer": self._no_info_message(question), "sources": [], "chunks_used": 0, "intent": intent}
        if stream:
            answer = self.generate_stream(question, context)
        else:
            answer = self.generate(question, context)
        seen_sources = set()
        unique_sources = []
        for c in chunks:
            src = c.get("metadata", {}).get("source")
            if src and src not in seen_sources:
                seen_sources.add(src)
                unique_sources.append({
                    "document_id": c.get("metadata", {}).get("document_id"),
                    "source": src,
                    "page": c.get("metadata", {}).get("page"),
                    "score": round(c.get("final_score", 0), 3),
                })
        result = {"answer": answer, "sources": unique_sources, "chunks_used": len(chunks), "intent": intent}
        if not stream:
            self.cache[cache_key] = result
        return result
