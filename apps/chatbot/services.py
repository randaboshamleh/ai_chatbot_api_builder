import logging
import threading
import time
from datetime import timedelta
from typing import Any, Dict

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from apps.analytics.models import QueryLog
from apps.chatbot.models import ChatMessage, ChatSession
from core.rag.pipeline import RAGPipeline

logger = logging.getLogger(__name__)

_PIPELINE_CACHE: Dict[str, Dict[str, Any]] = {}
_PIPELINE_CACHE_LOCK = threading.Lock()


def _pipeline_cache_ttl() -> int:
    value = getattr(settings, "RAG_PIPELINE_CACHE_TTL_SECONDS", 600)
    return max(60, int(value))


def get_tenant_pipeline(tenant) -> RAGPipeline:
    tenant_id = str(tenant.id)
    now = time.monotonic()
    ttl = _pipeline_cache_ttl()

    with _PIPELINE_CACHE_LOCK:
        entry = _PIPELINE_CACHE.get(tenant_id)
        if entry and (now - entry["last_used"]) < ttl:
            entry["last_used"] = now
            return entry["pipeline"]

        pipeline = RAGPipeline(tenant=tenant)
        _PIPELINE_CACHE[tenant_id] = {"pipeline": pipeline, "last_used": now}

        stale_keys = [
            key
            for key, value in _PIPELINE_CACHE.items()
            if (now - value["last_used"]) > (ttl * 2)
        ]
        for key in stale_keys:
            _PIPELINE_CACHE.pop(key, None)

        return pipeline


def get_today_query_count(tenant) -> int:
    now_local = timezone.localtime()
    start_of_day = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    return ChatMessage.objects.filter(
        session__tenant=tenant,
        created_at__gte=start_of_day,
        role="user",
    ).count()


def tenant_has_indexed_documents(tenant) -> bool:
    from apps.documents.models import Document

    cache_key = f"tenant:indexed_docs:{tenant.id}"
    cached = cache.get(cache_key)
    if cached is not None:
        return bool(cached)

    exists = Document.objects.filter(tenant=tenant, status="indexed").exists()
    ttl = max(10, int(getattr(settings, "RAG_INDEXED_DOCS_CACHE_TTL_SECONDS", 30)))
    cache.set(cache_key, bool(exists), timeout=ttl)
    return bool(exists)


def run_query(tenant, question: str) -> tuple[Dict[str, Any], float]:
    pipeline = get_tenant_pipeline(tenant)
    start = time.perf_counter()
    result = pipeline.query(question)
    response_time = time.perf_counter() - start
    return result, response_time


def run_stream_query(tenant, question: str):
    pipeline = get_tenant_pipeline(tenant)
    return pipeline.query(question, stream=True)


def get_or_create_session(tenant, session_id=None) -> ChatSession:
    if session_id:
        session, _ = ChatSession.objects.get_or_create(id=session_id, tenant=tenant)
        return session
    return ChatSession.objects.create(tenant=tenant)


def get_or_create_channel_session(tenant, channel: str, external_id: str) -> ChatSession:
    cache_key = f"chat:session:{tenant.id}:{channel}:{external_id}"
    cached_session_id = cache.get(cache_key)
    if cached_session_id:
        session = ChatSession.objects.filter(id=cached_session_id, tenant=tenant).first()
        if session:
            return session

    session = ChatSession.objects.create(tenant=tenant)
    ttl_seconds = int(
        getattr(settings, "CHANNEL_SESSION_CACHE_TTL_SECONDS", int(timedelta(days=7).total_seconds()))
    )
    cache.set(cache_key, str(session.id), timeout=max(3600, ttl_seconds))
    return session


def store_chat_exchange(
    *,
    session: ChatSession,
    question: str,
    answer: str,
    sources: list,
    user_metadata: dict | None = None,
    assistant_metadata: dict | None = None,
):
    ChatMessage.objects.create(
        session=session,
        role="user",
        content=question,
        metadata=user_metadata or {},
    )
    ChatMessage.objects.create(
        session=session,
        role="assistant",
        content=answer,
        sources=sources or [],
        metadata=assistant_metadata or {},
    )


def store_query_log(
    *,
    tenant,
    user,
    question: str,
    answer: str,
    response_time: float,
    chunks_used: int,
    sources: list,
):
    try:
        QueryLog.objects.create(
            tenant=tenant,
            user=user if getattr(user, "is_authenticated", False) else None,
            query=question,
            answer=answer,
            response_time=response_time,
            chunks_used=chunks_used,
            sources=sources or [],
        )
    except Exception as exc:
        logger.warning("Failed to write query log: %s", exc)
