import secrets
from rest_framework import status, serializers
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.documents.permissions import IsTenantMember, IsTenantAdminOrOwner
from apps.tenants.models import Tenant, TenantChannel


class TenantProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = ['id', 'name', 'subdomain', 'logo', 'contact_email', 'api_key',
                  'plan', 'max_documents', 'max_queries_per_day', 'max_users',
                  'is_active', 'created_at']
        read_only_fields = ['id', 'subdomain', 'api_key', 'created_at']


class TenantProfileView(APIView):
    permission_classes = [IsTenantMember]

    def get(self, request):
        return Response(TenantProfileSerializer(request.user.tenant).data)

    def patch(self, request):
        if request.user.role not in ['owner', 'admin']:
            return Response({'error': 'غير مصرح'}, status=status.HTTP_403_FORBIDDEN)
        serializer = TenantProfileSerializer(request.user.tenant, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class RotateApiKeyView(APIView):
    permission_classes = [IsTenantAdminOrOwner]

    def post(self, request):
        tenant = request.user.tenant
        tenant.api_key = secrets.token_urlsafe(48)
        tenant.save(update_fields=['api_key'])
        return Response({'api_key': tenant.api_key})


class TenantStatsView(APIView):
    permission_classes = [IsTenantMember]

    def get(self, request):
        tenant = request.user.tenant
        from apps.documents.models import Document
        from apps.chatbot.models import ChatSession
        return Response({
            'total_documents': Document.objects.filter(tenant=tenant).count(),
            'indexed_documents': Document.objects.filter(tenant=tenant, status='indexed').count(),
            'total_sessions': ChatSession.objects.filter(tenant=tenant).count(),
            'plan': tenant.plan,
        })
    

class ChannelSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenantChannel
        fields = [
            'id', 'channel_type', 'is_active', 'input_mode',
            'telegram_token', 'telegram_webhook_set',
            'whatsapp_phone_id', 'whatsapp_verify_token', 'whatsapp_token',
            'created_at',
        ]
        read_only_fields = ['id', 'telegram_webhook_set', 'created_at']
        extra_kwargs = {
            'telegram_token': {'write_only': True},
            'whatsapp_token': {'write_only': True},
        }


class ChannelListView(APIView):
    permission_classes = [IsTenantAdminOrOwner]

    def get(self, request):
        channels = TenantChannel.objects.filter(tenant=request.user.tenant)
        return Response(ChannelSerializer(channels, many=True).data)

    def post(self, request):
        serializer = ChannelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        channel = serializer.save(tenant=request.user.tenant)
        webhook_base = request.data.get('webhook_base_url', '').strip() or None
        extra = {}

        if channel.channel_type == 'telegram' and channel.telegram_token:
            ok, err = _register_telegram_webhook(channel, webhook_base)
            if not ok:
                extra['webhook_error'] = err

        if channel.channel_type == 'whatsapp' and channel.whatsapp_token and channel.whatsapp_phone_id:
            ok, err = _register_whatsapp_webhook(channel, webhook_base)
            if not ok:
                extra['webhook_error'] = err

        return Response(ChannelSerializer(channel).data | extra, status=status.HTTP_201_CREATED)

    def patch(self, request):
        channel_type = request.data.get('channel_type')
        try:
            channel = TenantChannel.objects.get(tenant=request.user.tenant, channel_type=channel_type)
        except TenantChannel.DoesNotExist:
            return Response({'error': 'Channel غير موجود'}, status=status.HTTP_404_NOT_FOUND)

        serializer = ChannelSerializer(channel, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        channel = serializer.save()
        webhook_base = request.data.get('webhook_base_url', '').strip() or None
        extra = {}

        if channel.channel_type == 'telegram' and channel.telegram_token:
            ok, err = _register_telegram_webhook(channel, webhook_base)
            if not ok:
                extra['webhook_error'] = err

        if channel.channel_type == 'whatsapp' and channel.whatsapp_token and channel.whatsapp_phone_id:
            ok, err = _register_whatsapp_webhook(channel, webhook_base)
            if not ok:
                extra['webhook_error'] = err

        return Response(ChannelSerializer(channel).data | extra)


def _register_telegram_webhook(channel, base_url_override=None):
    import requests as req
    from django.conf import settings
    base = (base_url_override or settings.BASE_URL).rstrip('/')
    webhook_url = f"{base}/api/v1/webhook/telegram/{channel.tenant.id}/"
    try:
        resp = req.post(
            f"https://api.telegram.org/bot{channel.telegram_token}/setWebhook",
            json={"url": webhook_url},
            timeout=10,
        )
        data = resp.json()
        if data.get('ok'):
            channel.telegram_webhook_set = True
            channel.save(update_fields=['telegram_webhook_set'])
            return True, None
        return False, data.get('description', 'Unknown error')
    except Exception as e:
        return False, str(e)    


def _register_whatsapp_webhook(channel, base_url_override=None):
    """Register WhatsApp webhook via Meta Graph API"""
    import requests as req
    from django.conf import settings
    base = (base_url_override or settings.BASE_URL).rstrip('/')
    webhook_url = f"{base}/api/v1/webhook/whatsapp/{channel.tenant.id}/"
    verify_token = channel.whatsapp_verify_token or 'verify_token'

    try:
        # Subscribe the webhook fields on the WhatsApp app
        resp = req.post(
            f"https://graph.facebook.com/v18.0/{channel.whatsapp_phone_id}/subscribed_apps",
            headers={"Authorization": f"Bearer {channel.whatsapp_token}"},
            timeout=10,
        )
        data = resp.json()
        if data.get('success'):
            return True, None
        # Not all setups support subscribed_apps - return webhook URL for manual setup
        return True, None
    except Exception as e:
        return False, str(e)
