import hashlib
import logging
import os
import re
import threading
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
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

logger = logging.getLogger(__name__)

RAG_PROMPT_TEMPLATE = """You are Assistify AI, a professional customer support assistant.
Your role is to answer customer questions accurately using ONLY the provided company documents.

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
  - Keep only unavoidable technical terms (product names/acronyms) in English.
- For English questions:
  - Reply in natural English.

## Source Accuracy Rules:
- Prioritize the most relevant details.
- If multiple sources conflict, pick the most directly matching chunk.
- Do not answer from unrelated chunks.

## Style:
- Keep response concise and direct.
- Start with the answer immediately.
- Use bullet points only if helpful.

Context:
{context}

Question: {question}

Answer:"""

SUMMARY_PROMPT = """Summarize the following text in 2-3 concise sentences. Focus on the key information only.

Text:
{text}

Summary:"""

MIN_RELEVANCE_SCORE = 0.45

TOKEN_RE = re.compile(r"[A-Za-z0-9_]+|[\u0600-\u06FF]+")
MIXED_SCRIPT_RE = re.compile(r"(?:[\u0600-\u06FF][A-Za-z])|(?:[A-Za-z][\u0600-\u06FF])")

AR_STOPWORDS: Set[str] = {
    "من", "الى", "إلى", "على", "في", "عن", "ما", "ماذا", "هل", "كيف", "كم", "لماذا", "اذا", "إذا",
    "هذا", "هذه", "ذلك", "تلك", "هناك", "مع", "أو", "او", "ثم", "لقد", "تم", "هي", "هو", "هم", "هن",
}

EN_STOPWORDS: Set[str] = {
    "the", "a", "an", "is", "are", "was", "were", "to", "of", "in", "on", "for", "from", "with", "at",
    "by", "and", "or", "as", "be", "can", "could", "should", "would", "what", "how", "when", "where",
    "why", "which", "that", "this", "these", "those",
}

INTENT_KEYWORDS = {
    "pricing": ["price", "pricing", "cost", "plan", "plans", "subscription", "fee", "payment", "billing", "discount", "package", "tier", "سعر", "أسعار", "تكلفة", "خطة", "اشتراك"],
    "features": ["feature", "features", "integration", "dashboard", "api", "capability", "function", "tool", "ميزة", "ميزات", "تكامل", "لوحة", "أداة"],
    "support": ["support", "help", "contact", "faq", "issue", "problem", "error", "bug", "how", "guide", "دعم", "مساعدة", "مشكلة", "خطأ", "كيف"],
    "onboarding": ["start", "setup", "install", "configure", "register", "signup", "getting", "بدء", "إعداد", "تسجيل"],
}


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

        self.answer_max_tokens = max(80, int(os.getenv('RAG_ANSWER_MAX_TOKENS', getattr(settings, 'RAG_ANSWER_MAX_TOKENS', 180))))
        self.summary_max_tokens = max(50, int(os.getenv('RAG_SUMMARY_MAX_TOKENS', getattr(settings, 'RAG_SUMMARY_MAX_TOKENS', 150))))
        self.llm_num_ctx = max(512, int(os.getenv('RAG_LLM_NUM_CTX', getattr(settings, 'RAG_LLM_NUM_CTX', 1536))))
        self.llm_temperature = float(os.getenv('RAG_LLM_TEMPERATURE', getattr(settings, 'RAG_LLM_TEMPERATURE', 0.1)))
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
        self.min_arabic_answer_ratio = float(
            os.getenv(
                'RAG_MIN_ARABIC_ANSWER_RATIO',
                getattr(settings, 'RAG_MIN_ARABIC_ANSWER_RATIO', 0.72),
            )
        )

        self.include_summaries_in_query = os.getenv(
            'RAG_INCLUDE_SUMMARIES_IN_QUERY',
            str(getattr(settings, 'RAG_INCLUDE_SUMMARIES_IN_QUERY', False)),
        ).lower() == 'true'

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
        return re.sub(r"\s+", " ", (query or "").strip()).lower()

    def _cache_key(self, query: str) -> str:
        return hashlib.md5(self._normalize_query_for_cache(query).encode("utf-8")).hexdigest()

    def _result_cache_key(self, query: str) -> str:
        return f"rag:result:{self.tenant.id}:{self._cache_key(query)}"

    def _summary_cache_key(self, level: str, category: str) -> str:
        return f"rag:summary:{self.tenant.id}:{level}:{category}"

    def _is_arabic(self, text: str) -> bool:
        if not text:
            return False
        arabic_chars = sum(1 for c in text if "\u0600" <= c <= "\u06ff")
        return arabic_chars > len(text) * 0.25

    def _arabic_ratio(self, text: str) -> float:
        if not text:
            return 0.0
        ar = sum(1 for c in text if "\u0600" <= c <= "\u06ff")
        letters = sum(1 for c in text if c.isalpha())
        if letters == 0:
            return 0.0
        return ar / letters

    def _tokenize(self, text: str) -> List[str]:
        tokens = []
        for raw in TOKEN_RE.findall((text or '').lower()):
            if len(raw) < 2:
                continue
            if raw in EN_STOPWORDS or raw in AR_STOPWORDS:
                continue
            tokens.append(raw)
        return tokens

    def _no_info_message(self, question: str) -> str:
        if self._is_arabic(question):
            return "ما لقيت الإجابة بشكل واضح في الوثائق الحالية."
        return "I could not find a clear answer in the available documents."

    def _service_unavailable_message(self, question: str) -> str:
        if self._is_arabic(question):
            return "الخدمة الذكية بطيئة أو غير متاحة حالياً. حاول مجددًا بعد قليل."
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
        semantic_k = max(k, self.max_detail_chunks * 2)

        try:
            semantic_results = self.vector_store.similarity_search(query, k=semantic_k)
        except Exception:
            semantic_results = []

        max_semantic = max((r.get('similarity_score', 0.0) for r in semantic_results), default=0.0)
        query_tokens = self._tokenize(query)
        should_use_keyword = (
            self.enable_keyword_search
            and len(query_tokens) >= 2
            and (
                not semantic_results
                or max_semantic < self.keyword_fallback_threshold
                or self._is_arabic(query)
            )
        )

        keyword_results: List[Dict] = []
        if should_use_keyword:
            try:
                keyword_results = self.vector_store.keyword_search(query, k=max(k, semantic_k))
            except Exception:
                keyword_results = []

        combined = semantic_results + keyword_results
        seen = set()
        unique = []
        for row in combined:
            content = row.get('content')
            if content and content not in seen:
                seen.add(content)
                unique.append(row)
        return unique

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
            density_bonus = min(len(scores), 3) * 0.02
            document_scores[doc_key] = (top1 * 0.74) + (top2_avg * 0.24) + density_bonus

        for chunk in chunks:
            doc_key = self._document_key(chunk)
            doc_score = document_scores.get(doc_key, 0.0)
            chunk['document_score'] = round(doc_score, 4)
            chunk['final_score'] = round(float(chunk.get('final_score', 0.0)) + (doc_score * 0.10), 4)

    def _rank_documents(self, ranked_chunks: List[Dict]) -> List[Tuple[str, float]]:
        scores: Dict[str, float] = {}
        for chunk in ranked_chunks:
            doc_key = self._document_key(chunk)
            score = float(chunk.get('document_score', chunk.get('final_score', 0.0)))
            if score > scores.get(doc_key, -1.0):
                scores[doc_key] = score
        return sorted(scores.items(), key=lambda row: row[1], reverse=True)

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
        q_tokens = self._tokenize(query)
        q_token_set = set(q_tokens)
        q_lower = query.lower()

        for chunk in chunks:
            semantic_score = float(chunk.get('similarity_score', 0.0))
            content = chunk.get('content', '')
            content_tokens = set(self._tokenize(content[:1200]))

            overlap = 0.0
            if q_token_set:
                overlap = len(q_token_set.intersection(content_tokens)) / len(q_token_set)

            phrase_bonus = 0.0
            if len(q_lower) <= 100 and q_lower in content.lower():
                phrase_bonus = 0.10

            source = str(chunk.get('metadata', {}).get('source', '')).lower()
            source_tokens = set(self._tokenize(source))
            source_overlap = len(q_token_set.intersection(source_tokens))
            source_bonus = min(0.08, source_overlap * 0.03)

            final_score = (semantic_score * 0.55) + (overlap * 0.45) + phrase_bonus + source_bonus
            chunk['lexical_overlap'] = round(overlap, 3)
            chunk['final_score'] = round(final_score, 4)

        self._apply_document_boost(chunks)
        chunks.sort(key=lambda x: x.get('final_score', 0.0), reverse=True)

        relevant = [c for c in chunks if c.get('final_score', 0.0) >= self.min_relevance_score]
        if not relevant:
            relevant = chunks[: max(1, self.max_detail_chunks)]

        selected = self._select_diverse_chunks(relevant)

        for chunk in selected:
            logger.info(
                'Selected chunk score=%.3f overlap=%.3f doc_score=%.3f source=%s',
                chunk.get('final_score', 0.0),
                chunk.get('lexical_overlap', 0.0),
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

    def build_hierarchical_context(self, intent: str, detail_chunks: List[Dict]) -> str:
        parts = []

        # Put detailed evidence first to avoid wrong-source bias.
        for index, chunk in enumerate(detail_chunks):
            source = chunk.get('metadata', {}).get('source', '')
            page = chunk.get('metadata', {}).get('page', '')
            text = chunk.get('content', '')[:700]
            score = chunk.get('final_score', 0)
            parts.append(f"[Evidence {index + 1} | source={source} | page={page} | score={score}]\n{text}")

        if self.include_summaries_in_query:
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

    def _model_for_query(self, query: str) -> str:
        if self._is_arabic(query) and self.model_arabic:
            return self.model_arabic
        return self.model

    def _run_with_timeout(self, fn: Callable[[], Any], timeout_seconds: float):
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(fn)
            try:
                return future.result(timeout=timeout_seconds)
            except FutureTimeoutError as exc:
                future.cancel()
                raise TimeoutError(f"LLM call exceeded timeout of {timeout_seconds:.1f}s") from exc

    def _llm_generate(self, prompt: str, max_tokens: int, model_name: str, timeout_seconds: float | None = None) -> str:
        timeout_seconds = timeout_seconds or self.max_response_seconds
        started = time.perf_counter()
        response = self._run_with_timeout(
            lambda: self.llm_client.generate(
                model=model_name,
                prompt=prompt,
                keep_alive='10m',
                options={
                    'temperature': self.llm_temperature,
                    'num_predict': max_tokens,
                    'top_p': self.llm_top_p,
                    'num_ctx': self.llm_num_ctx,
                },
            ),
            timeout_seconds=float(timeout_seconds),
        )
        duration = time.perf_counter() - started
        logger.info('LLM generate completed in %.2fs using model=%s', duration, model_name)
        return response['response'].strip()

    def _needs_arabic_rewrite(self, query: str, answer: str) -> bool:
        if not self._is_arabic(query):
            return False
        if len(answer.strip()) < 15:
            return False
        if self._arabic_ratio(answer) < self.min_arabic_answer_ratio:
            return True
        return bool(MIXED_SCRIPT_RE.search(answer))

    def _rewrite_in_arabic(self, answer: str, query: str) -> str:
        model_name = self._model_for_query(query)
        prompt = (
            'أعد صياغة النص التالي إلى عربية واضحة وسليمة فقط. '\
            'لا تضف أي معلومة جديدة، ولا تكتب بالإنجليزية إلا أسماء المنتجات أو الاختصارات الضرورية.\n\n'
            f'النص:\n{answer}\n\n'
            'النص المصحح:'
        )
        try:
            return self._llm_generate(prompt, max_tokens=self.answer_max_tokens, model_name=model_name)
        except Exception:
            return answer

    def generate(self, query: str, context: str) -> str:
        if not OLLAMA_AVAILABLE or not self.llm_client:
            return self._service_unavailable_message(query)

        prompt = RAG_PROMPT_TEMPLATE.format(context=context, question=query)
        model_name = self._model_for_query(query)
        try:
            answer = self._llm_generate(prompt, max_tokens=self.answer_max_tokens, model_name=model_name)
            if re.search(r"\bNO_INFO\b", answer, flags=re.IGNORECASE) or len(answer.strip()) < 5:
                return self._no_info_message(query)

            if self._needs_arabic_rewrite(query, answer):
                answer = self._rewrite_in_arabic(answer, query).strip()

            return answer.replace('\x00', '').strip()
        except Exception as exc:
            logger.error('Failed to generate response: %s', exc)
            return self._service_unavailable_message(query)

    def generate_stream(self, query: str, context: str):
        if not OLLAMA_AVAILABLE or not self.llm_client:
            yield self._service_unavailable_message(query)
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
                if chunk.get('response'):
                    yield chunk['response']
        except Exception as exc:
            logger.error('Streaming failed: %s', exc)
            yield self._service_unavailable_message(query)

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
        question = (question or '').strip()
        if not question:
            return {'answer': 'Please send a valid question.', 'sources': [], 'chunks_used': 0, 'intent': 'general'}

        cache_key = self._result_cache_key(question)
        if not stream and self.query_cache_ttl > 0:
            cached_result = cache.get(cache_key)
            if cached_result:
                logger.info('RAG cache hit for tenant %s', self.tenant.id)
                return cached_result

        t0 = time.perf_counter()
        intent = self.detect_intent(question)

        t_retrieve_start = time.perf_counter()
        chunks = self.retrieve(question, k=self.retrieval_k)
        chunks = self.rerank(question, chunks)
        t_retrieve = time.perf_counter() - t_retrieve_start

        context = self.build_hierarchical_context(intent, chunks)
        if not context:
            return {'answer': self._no_info_message(question), 'sources': [], 'chunks_used': 0, 'intent': intent}

        if stream:
            answer = self.generate_stream(question, context)
        else:
            answer = self.generate(question, context)

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

        if not stream and self.query_cache_ttl > 0:
            cache.set(cache_key, result, timeout=self.query_cache_ttl)

        return result
