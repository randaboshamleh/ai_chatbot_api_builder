# apps/chatbot/web_chat_views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.shortcuts import get_object_or_404
from apps.tenants.models import Tenant, TenantChannel
from apps.chatbot.models import ChatSession, ChatMessage
from core.rag.pipeline import RAGPipeline
import uuid


class WebChatInitView(APIView):
    """
    Initialize a web chat session
    No authentication required - public endpoint
    """
    permission_classes = [AllowAny]

    def post(self, request):
        tenant_slug = request.data.get('tenant_slug')
        
        if not tenant_slug:
            response = Response(
                {'error': 'tenant_slug is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
            # Add CORS headers
            response["Access-Control-Allow-Origin"] = "*"
            response["Access-Control-Allow-Methods"] = "POST, OPTIONS"
            response["Access-Control-Allow-Headers"] = "Content-Type"
            return response
        
        # Get tenant
        tenant = get_object_or_404(Tenant, subdomain=tenant_slug)
        
        # Check if web channel is enabled
        web_channel = TenantChannel.objects.filter(
            tenant=tenant,
            channel_type='web',
            is_active=True
        ).first()
        
        if not web_channel:
            return Response(
                {'error': 'Web chat is not enabled for this tenant'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Create or get session
        session_id = request.data.get('session_id')
        
        if session_id:
            session = ChatSession.objects.filter(
                id=session_id,
                tenant=tenant
            ).first()
        else:
            session = None
        
        if not session:
            session = ChatSession.objects.create(
                tenant=tenant,
                user=None,  # Anonymous web chat
            )
        
        return Response({
            'session_id': str(session.id),
            'tenant_name': tenant.name,
            'welcome_message': 'Hello! How can I help you?'
        })


class WebChatMessageView(APIView):
    """
    Send a message in web chat
    No authentication required - public endpoint
    """
    permission_classes = [AllowAny]

    def post(self, request):
        session_id = request.data.get('session_id')
        message = request.data.get('message')
        
        if not session_id or not message:
            return Response(
                {'error': 'session_id and message are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get session
        session = get_object_or_404(ChatSession, id=session_id)
        
        # Check if web channel is enabled
        web_channel = TenantChannel.objects.filter(
            tenant=session.tenant,
            channel_type='web',
            is_active=True
        ).first()
        
        if not web_channel:
            return Response(
                {'error': 'Web chat is not enabled'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Save user message
        user_message = ChatMessage.objects.create(
            session=session,
            role='user',
            content=message
        )
        
        # Generate response using RAG
        try:
            rag = RAGPipeline(tenant=session.tenant)
            result = rag.query(message)
            
            response_text = result.get('answer', 'عذراً، لم أتمكن من الإجابة.')
            sources = result.get('sources', [])
            
            # Save assistant message
            assistant_message = ChatMessage.objects.create(
                session=session,
                role='assistant',
                content=response_text,
                sources=sources
            )
            
            return Response({
                'message_id': str(assistant_message.id),
                'response': response_text,
                'sources': sources,
                'timestamp': assistant_message.created_at.isoformat()
            })
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f'Web chat error: {str(e)}')
            
            return Response(
                {'error': f'Failed to generate response: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class WebChatHistoryView(APIView):
    """
    Get chat history for a session
    No authentication required - public endpoint
    """
    permission_classes = [AllowAny]

    def get(self, request, session_id):
        session = get_object_or_404(ChatSession, id=session_id)
        
        messages = ChatMessage.objects.filter(session=session).order_by('created_at')
        
        history = []
        for msg in messages:
            history.append({
                'id': str(msg.id),
                'role': msg.role,
                'content': msg.content,
                'sources': msg.sources,
                'timestamp': msg.created_at.isoformat()
            })
        
        return Response({
            'session_id': str(session.id),
            'messages': history
        })
