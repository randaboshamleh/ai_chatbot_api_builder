import logging
import threading

from django.conf import settings
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView

from apps.chatbot.channel_processors import (
    process_telegram_message_sync,
    process_whatsapp_message_sync,
    send_telegram_message,
)
from apps.tenants.models import TenantChannel

logger = logging.getLogger(__name__)


def _run_in_background(target, *args):
    thread = threading.Thread(target=target, args=args, daemon=True)
    thread.start()


def _process_telegram_background(tenant_id, chat_id, text, token):
    try:
        process_telegram_message_sync(str(tenant_id), chat_id, text, token)
    except Exception as exc:
        logger.error("Telegram background processing failed: %s", exc)
        send_telegram_message(token, chat_id, "عذراً، حدث خطأ أثناء معالجة سؤالك. حاول مرة أخرى.")


def _dispatch_telegram_message(tenant_id, chat_id, text, token):
    mode = str(getattr(settings, "TELEGRAM_PROCESSING_MODE", "thread")).strip().lower()

    if mode == "sync":
        _process_telegram_background(tenant_id, chat_id, text, token)
        return

    if mode == "celery":
        try:
            from workers.tasks import process_telegram_message

            process_telegram_message.delay(str(tenant_id), chat_id, text, token)
            return
        except Exception as exc:
            logger.warning("Telegram Celery dispatch failed, falling back to thread mode: %s", exc)

    _run_in_background(_process_telegram_background, tenant_id, chat_id, text, token)


def _process_whatsapp_background(tenant_id, phone, text, token, phone_id):
    try:
        process_whatsapp_message_sync(str(tenant_id), phone, text, token, phone_id)
    except Exception as exc:
        logger.error("WhatsApp background processing failed: %s", exc)


def _dispatch_whatsapp_message(tenant_id, phone, text, token, phone_id):
    mode = str(getattr(settings, "WHATSAPP_PROCESSING_MODE", "celery")).strip().lower()

    if mode == "sync":
        _process_whatsapp_background(tenant_id, phone, text, token, phone_id)
        return

    if mode == "celery":
        try:
            from workers.tasks import process_whatsapp_message

            process_whatsapp_message.delay(str(tenant_id), phone, text, token, phone_id)
            return
        except Exception as exc:
            logger.warning("WhatsApp Celery dispatch failed, falling back to thread mode: %s", exc)

    _run_in_background(_process_whatsapp_background, tenant_id, phone, text, token, phone_id)


@method_decorator(csrf_exempt, name='dispatch')
class TelegramWebhookView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, tenant_id):
        try:
            channel = TenantChannel.objects.get(
                tenant_id=tenant_id,
                channel_type='telegram',
                is_active=True,
            )
        except TenantChannel.DoesNotExist:
            return HttpResponse(status=200)

        payload = request.data or {}
        message = payload.get('message') or payload.get('edited_message') or {}
        chat_id = message.get('chat', {}).get('id')
        text = (message.get('text') or '').strip()

        if not chat_id:
            return HttpResponse(status=200)

        if text == '/start':
            send_telegram_message(
                channel.telegram_token,
                chat_id,
                (
                    "مرحباً! أنا مساعدك الذكي. أرسل سؤالك وسأجيبك بناءً على الوثائق المتاحة.\n\n"
                    "Hello! I'm your AI assistant. Send me a question and I'll answer based on the available documents."
                ),
            )
            return HttpResponse(status=200)

        if not text:
            return HttpResponse(status=200)

        _dispatch_telegram_message(tenant_id, chat_id, text, channel.telegram_token)
        return HttpResponse(status=200)


@method_decorator(csrf_exempt, name='dispatch')
class WhatsAppWebhookView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, tenant_id):
        """Webhook verification"""
        try:
            channel = TenantChannel.objects.get(
                tenant_id=tenant_id,
                channel_type='whatsapp',
            )
        except TenantChannel.DoesNotExist:
            return HttpResponse(status=403)

        verify_token = request.GET.get('hub.verify_token')
        challenge = request.GET.get('hub.challenge')

        if verify_token == channel.whatsapp_verify_token:
            return HttpResponse(challenge)
        return HttpResponse(status=403)

    def post(self, request, tenant_id):
        try:
            channel = TenantChannel.objects.get(
                tenant_id=tenant_id,
                channel_type='whatsapp',
                is_active=True,
            )
        except TenantChannel.DoesNotExist:
            return HttpResponse(status=200)

        try:
            entry = request.data['entry'][0]
            changes = entry['changes'][0]['value']
            messages = changes.get('messages', [])

            if not messages:
                return HttpResponse(status=200)

            message = messages[0]
            phone = message['from']
            msg_type = message['type']
            text = ''

            if msg_type == 'text':
                text = message['text']['body']

            if not text:
                return HttpResponse(status=200)

            _dispatch_whatsapp_message(
                tenant_id,
                phone,
                text,
                channel.whatsapp_token,
                channel.whatsapp_phone_id,
            )

        except Exception as exc:
            logger.error("WhatsApp webhook error: %s", exc)

        return HttpResponse(status=200)
