import logging
import re
from typing import Iterable

import requests

from apps.chatbot.preprocessing import preprocess_user_text
from apps.tenants.models import Tenant
from apps.chatbot.services import (
    get_or_create_channel_session,
    run_query,
    store_chat_exchange,
)

logger = logging.getLogger(__name__)

TELEGRAM_MAX_MESSAGE_LENGTH = 3900
WHATSAPP_MAX_MESSAGE_LENGTH = 3800
ARABIC_RE = re.compile(r"[\u0600-\u06FF]")


def _chunk_text(text: str, chunk_size: int) -> Iterable[str]:
    if len(text) <= chunk_size:
        yield text
        return

    start = 0
    while start < len(text):
        yield text[start:start + chunk_size]
        start += chunk_size


def _is_arabic_text(text: str) -> bool:
    return bool(ARABIC_RE.search(text or ""))


def send_telegram_typing(token: str, chat_id) -> None:
    endpoint = f"https://api.telegram.org/bot{token}/sendChatAction"
    try:
        requests.post(
            endpoint,
            json={"chat_id": chat_id, "action": "typing"},
            timeout=8,
        )
    except Exception as exc:
        logger.debug("Telegram typing action failed: %s", exc)


def send_telegram_message(token: str, chat_id, text: str) -> None:
    if not text:
        return

    endpoint = f"https://api.telegram.org/bot{token}/sendMessage"
    for part in _chunk_text(text, TELEGRAM_MAX_MESSAGE_LENGTH):
        try:
            requests.post(
                endpoint,
                json={"chat_id": chat_id, "text": part},
                timeout=12,
            )
        except Exception as exc:
            logger.error("Telegram send error: %s", exc)


def process_telegram_message_sync(tenant_id: str, chat_id, text: str, token: str):
    tenant = Tenant.objects.get(id=tenant_id)
    session = get_or_create_channel_session(tenant, "telegram", str(chat_id))
    normalized_text = preprocess_user_text(text)
    if not normalized_text:
        return

    send_telegram_typing(token, chat_id)
    result, _response_time = run_query(tenant, normalized_text)
    fallback = (
        "عذرًا، لم أتمكن من توليد إجابة واضحة الآن."
        if _is_arabic_text(normalized_text)
        else "Sorry, I could not generate a response."
    )
    answer = result.get("answer", "").strip() or fallback
    sources = result.get("sources", [])

    metadata = {"channel": "telegram", "external_chat_id": str(chat_id)}
    store_chat_exchange(
        session=session,
        question=normalized_text,
        answer=answer,
        sources=sources,
        user_metadata=metadata,
        assistant_metadata=metadata,
    )
    send_telegram_message(token, chat_id, answer)


def send_whatsapp_message(token: str, phone_id: str, phone: str, text: str) -> None:
    if not text:
        return

    endpoint = f"https://graph.facebook.com/v18.0/{phone_id}/messages"
    headers = {"Authorization": f"Bearer {token}"}
    for part in _chunk_text(text, WHATSAPP_MAX_MESSAGE_LENGTH):
        try:
            requests.post(
                endpoint,
                headers=headers,
                json={
                    "messaging_product": "whatsapp",
                    "to": phone,
                    "type": "text",
                    "text": {"body": part},
                },
                timeout=12,
            )
        except Exception as exc:
            logger.error("WhatsApp send error: %s", exc)


def process_whatsapp_message_sync(tenant_id: str, phone: str, text: str, token: str, phone_id: str):
    tenant = Tenant.objects.get(id=tenant_id)
    session = get_or_create_channel_session(tenant, "whatsapp", phone)
    normalized_text = preprocess_user_text(text)
    if not normalized_text:
        return

    result, _response_time = run_query(tenant, normalized_text)
    answer = result.get("answer", "").strip() or "Sorry, I could not generate a response."
    sources = result.get("sources", [])

    metadata = {"channel": "whatsapp", "external_chat_id": phone}
    store_chat_exchange(
        session=session,
        question=normalized_text,
        answer=answer,
        sources=sources,
        user_metadata=metadata,
        assistant_metadata=metadata,
    )
    send_whatsapp_message(token, phone_id, phone, answer)
