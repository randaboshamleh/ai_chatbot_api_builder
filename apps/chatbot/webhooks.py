import json
import logging
import requests
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.views import APIView
from rest_framework.response import Response
from apps.tenants.models import Tenant, TenantChannel
from apps.chatbot.models import ChatSession, ChatMessage
from core.rag.pipeline import RAGPipeline

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
        voice = message.get('voice')

        if not chat_id:
            return HttpResponse(status=200)

        # Voice message
        if voice and channel.input_mode in ['voice', 'both']:
            text = _transcribe_telegram_voice(voice, channel.telegram_token)

        if not text:
            return HttpResponse(status=200)

        # RAG
        try:
            session, _ = ChatSession.objects.get_or_create(
                tenant=channel.tenant,
                defaults={'tenant': channel.tenant}
            )
            pipeline = RAGPipeline(tenant=channel.tenant)
            result = pipeline.query(text)

            ChatMessage.objects.create(session=session, role='user', content=text)
            ChatMessage.objects.create(
                session=session, role='assistant',
                content=result['answer'], sources=result['sources']
            )

            _send_telegram_message(channel.telegram_token, chat_id, result['answer'])
        except Exception as e:
            logger.error(f"Telegram webhook error: {e}")
            _send_telegram_message(channel.telegram_token, chat_id, "عذراً، حدث خطأ. حاول مرة أخرى.")

        return HttpResponse(status=200)


def _send_telegram_message(token, chat_id, text):
    requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": text},
        timeout=10,
    )


def _transcribe_telegram_voice(voice, token):
    try:
        file_id = voice['file_id']
        file_info = requests.get(
            f"https://api.telegram.org/bot{token}/getFile",
            params={"file_id": file_id}
        ).json()
        file_path = file_info['result']['file_path']
        audio_url = f"https://api.telegram.org/file/bot{token}/{file_path}"
        audio_data = requests.get(audio_url).content

        import whisper, tempfile, os
        model = whisper.load_model("base")
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
            f.write(audio_data)
            tmp_path = f.name
        result = model.transcribe(tmp_path)
        os.unlink(tmp_path)
        return result['text']
    except Exception as e:
        logger.error(f"Voice transcription error: {e}")
        return ""


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
            elif msg_type == 'audio' and channel.input_mode in ['voice', 'both']:
                audio_id = message['audio']['id']
                text = _transcribe_whatsapp_voice(audio_id, channel.whatsapp_token)

            if not text:
                return HttpResponse(status=200)

            pipeline = RAGPipeline(tenant=channel.tenant)
            result = pipeline.query(text)
            _send_whatsapp_message(channel, phone, result['answer'])

        except Exception as e:
            logger.error(f"WhatsApp webhook error: {e}")

        return HttpResponse(status=200)


def _send_whatsapp_message(channel, phone, text):
    requests.post(
        f"https://graph.facebook.com/v18.0/{channel.whatsapp_phone_id}/messages",
        headers={"Authorization": f"Bearer {channel.whatsapp_token}"},
        json={
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "text",
            "text": {"body": text},
        },
        timeout=10,
    )


def _transcribe_whatsapp_voice(audio_id, token):
    try:
        media_url = requests.get(
            f"https://graph.facebook.com/v18.0/{audio_id}",
            headers={"Authorization": f"Bearer {token}"},
        ).json().get('url')

        audio_data = requests.get(
            media_url,
            headers={"Authorization": f"Bearer {token}"},
        ).content

        import whisper, tempfile, os
        model = whisper.load_model("base")
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
            f.write(audio_data)
            tmp_path = f.name
        result = model.transcribe(tmp_path)
        os.unlink(tmp_path)
        return result['text']
    except Exception as e:
        logger.error(f"WhatsApp voice error: {e}")
        return ""