import json
import logging
import requests
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.views import APIView
from apps.tenants.models import TenantChannel

logger = logging.getLogger(__name__)


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

        data = request.data
        message = data.get('message', {})
        chat_id = message.get('chat', {}).get('id')
        text = message.get('text', '').strip()

        if not chat_id:
            return HttpResponse(status=200)

        # Handle /start command
        if text == '/start':
            _send_telegram_message(
                channel.telegram_token,
                chat_id,
                "مرحباً! أنا مساعدك الذكي. أرسل سؤالك وسأجيبك بناءً على الوثائق المتاحة.\n\nHello! I'm your AI assistant. Send me a question and I'll answer based on the available documents."
            )
            return HttpResponse(status=200)

        if not text:
            return HttpResponse(status=200)

        # Dispatch async Celery task - return 200 immediately to Telegram
        try:
            from workers.tasks import process_telegram_message
            process_telegram_message.delay(
                str(tenant_id),
                chat_id,
                text,
                channel.telegram_token,
            )
        except Exception as e:
            logger.error(f"Failed to dispatch Telegram task: {e}")
            _send_telegram_message(channel.telegram_token, chat_id, "عذراً، حدث خطأ. حاول مرة أخرى.")

        return HttpResponse(status=200)


def _send_telegram_message(token, chat_id, text):
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=10,
        )
    except Exception as e:
        logger.error(f"Failed to send Telegram message: {e}")


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

            # Dispatch async
            from workers.tasks import process_whatsapp_message
            process_whatsapp_message.delay(
                str(tenant_id),
                phone,
                text,
                channel.whatsapp_token,
                channel.whatsapp_phone_id,
            )

        except Exception as e:
            logger.error(f"WhatsApp webhook error: {e}")

        return HttpResponse(status=200)
