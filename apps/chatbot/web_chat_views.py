from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.chatbot.models import ChatMessage, ChatSession
from apps.chatbot.services import run_query
from apps.tenants.models import Tenant, TenantChannel


class WebChatInitView(APIView):
    """
    Initialize a web chat session.
    No authentication required - public endpoint.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        tenant_slug = request.data.get('tenant_slug')
        if not tenant_slug:
            response = Response({'error': 'tenant_slug is required'}, status=status.HTTP_400_BAD_REQUEST)
            response['Access-Control-Allow-Origin'] = '*'
            response['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
            response['Access-Control-Allow-Headers'] = 'Content-Type'
            return response

        tenant = get_object_or_404(Tenant, subdomain=tenant_slug)

        web_channel = TenantChannel.objects.filter(
            tenant=tenant,
            channel_type='web',
            is_active=True,
        ).first()
        if not web_channel:
            return Response({'error': 'Web chat is not enabled for this tenant'}, status=status.HTTP_403_FORBIDDEN)

        session_id = request.data.get('session_id')
        if session_id:
            session = ChatSession.objects.filter(id=session_id, tenant=tenant).first()
        else:
            session = None

        if not session:
            session = ChatSession.objects.create(tenant=tenant, user=None)

        return Response(
            {
                'session_id': str(session.id),
                'tenant_name': tenant.name,
                'welcome_message': 'Hello! How can I help you?',
            }
        )


class WebChatMessageView(APIView):
    """
    Send a message in web chat.
    No authentication required - public endpoint.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        session_id = request.data.get('session_id')
        message = (request.data.get('message') or '').strip()

        if not session_id or not message:
            return Response({'error': 'session_id and message are required'}, status=status.HTTP_400_BAD_REQUEST)

        session = get_object_or_404(ChatSession.objects.select_related('tenant'), id=session_id)

        web_channel = TenantChannel.objects.filter(
            tenant=session.tenant,
            channel_type='web',
            is_active=True,
        ).first()
        if not web_channel:
            return Response({'error': 'Web chat is not enabled'}, status=status.HTTP_403_FORBIDDEN)

        try:
            result, _response_time = run_query(session.tenant, message)
            response_text = result.get('answer', 'عذراً، لم أتمكن من الإجابة.')
            sources = result.get('sources', [])

            ChatMessage.objects.create(session=session, role='user', content=message)
            assistant_message = ChatMessage.objects.create(
                session=session,
                role='assistant',
                content=response_text,
                sources=sources,
            )

            return Response(
                {
                    'message_id': str(assistant_message.id),
                    'response': response_text,
                    'sources': sources,
                    'timestamp': assistant_message.created_at.isoformat(),
                }
            )
        except Exception as exc:
            import logging

            logger = logging.getLogger(__name__)
            logger.error('Web chat error: %s', str(exc))
            return Response(
                {'error': f'Failed to generate response: {str(exc)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class WebChatHistoryView(APIView):
    """
    Get chat history for a session.
    No authentication required - public endpoint.
    """

    permission_classes = [AllowAny]

    def get(self, request, session_id):
        session = get_object_or_404(ChatSession, id=session_id)
        messages = ChatMessage.objects.filter(session=session).order_by('created_at')

        history = [
            {
                'id': str(msg.id),
                'role': msg.role,
                'content': msg.content,
                'sources': msg.sources,
                'timestamp': msg.created_at.isoformat(),
            }
            for msg in messages
        ]

        return Response({'session_id': str(session.id), 'messages': history})
