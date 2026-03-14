import logging
import time
from datetime import date
from rest_framework.parsers import MultiPartParser
from django.http import StreamingHttpResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.chatbot.models import ChatSession, ChatMessage
from apps.chatbot.serializers import ChatQuerySerializer
from apps.documents.permissions import IsTenantMember
from core.rag.pipeline import RAGPipeline
from apps.tenants.models import Tenant


logger = logging.getLogger(__name__)


class ChatQueryView(APIView):
    permission_classes = [IsTenantMember]

    def post(self, request):
        tenant = request.user.tenant

        serializer = ChatQuerySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        question = serializer.validated_data['question']
        stream = serializer.validated_data.get('stream', False)
        session_id = serializer.validated_data.get('session_id')

        today_count = ChatMessage.objects.filter(
            session__tenant=tenant,
            created_at__date=date.today(),
            role='user',
        ).count()

        if today_count >= tenant.max_queries_per_day:
            return Response({'error': 'تجاوزت الحد اليومي'}, status=status.HTTP_429_TOO_MANY_REQUESTS)

        from apps.documents.models import Document
        if not Document.objects.filter(tenant=tenant, status='indexed').exists():
            return Response({'error': 'لا توجد وثائق مفهرسة بعد'}, status=status.HTTP_404_NOT_FOUND)

        if session_id:
            session, _ = ChatSession.objects.get_or_create(id=session_id, tenant=tenant)
        else:
            session = ChatSession.objects.create(tenant=tenant)

        ChatMessage.objects.create(session=session, role='user', content=question)

        try:
            pipeline = RAGPipeline(tenant=tenant)

            if stream:
                return self._stream_response(pipeline, question, session)

            start_time = time.time()
            result = pipeline.query(question)
            response_time = time.time() - start_time
            
            ChatMessage.objects.create(
                session=session,
                role='assistant',
                content=result['answer'],
                sources=result['sources'],
            )
            
            # Log query for analytics
            from apps.analytics.models import QueryLog
            QueryLog.objects.create(
                tenant=tenant,
                user=request.user if request.user.is_authenticated else None,
                query=question,
                answer=result['answer'],
                response_time=response_time,
                chunks_used=result['chunks_used'],
                sources=result['sources'],
            )
            
            return Response({
                'session_id': str(session.id),
                'answer': result['answer'],
                'sources': result['sources'],
                'chunks_used': result['chunks_used'],
            })

        except Exception as e:
            logger.error(f"RAG error: {e}")
            return Response({'error': 'حدث خطأ أثناء معالجة السؤال'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _stream_response(self, pipeline, question, session):
        def event_stream():
            full_response = []
            try:
                result = pipeline.query(question, stream=True)
                for token in result['answer']:
                    full_response.append(token)
                    yield f"data: {token}\n\n"
                
                # حفظ الرسالة الكاملة بعد انتهاء التدفق
                ChatMessage.objects.create(
                    session=session,
                    role='assistant',
                    content=''.join(full_response),
                    sources=result.get('sources', []),
                )
                yield "data: [DONE]\n\n"
            except Exception as e:
                logger.error(f"Streaming error: {e}")
                yield f"data: [ERROR] {str(e)}\n\n"

        response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
        response['Cache-Control'] = 'no-cache'
        response['Connection'] = 'keep-alive'
        return response
    

class VoiceQueryView(APIView):
    permission_classes = [IsTenantMember]
    parser_classes = [MultiPartParser]

    def post(self, request):
        tenant = request.user.tenant

        audio_file = request.FILES.get('audio')
        if not audio_file:
            return Response({'error': 'الملف الصوتي مطلوب'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            import whisper, tempfile, os
            model = whisper.load_model("base")
            with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
                for chunk in audio_file.chunks():
                    f.write(chunk)
                tmp_path = f.name

            transcription = model.transcribe(tmp_path)
            os.unlink(tmp_path)
            question = transcription['text'].strip()

            if not question:
                return Response({'error': 'ما تم التعرف على الصوت'}, status=status.HTTP_400_BAD_REQUEST)

            pipeline = RAGPipeline(tenant=tenant)
            result = pipeline.query(question)

            return Response({
                'question': question,
                'answer': result['answer'],
                'sources': result['sources'],
            })
        except Exception as e:
            logger.error(f"Voice query error: {e}")
            return Response({'error': 'خطأ في معالجة الصوت'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ChatSessionListView(APIView):
    permission_classes = [IsTenantMember]

    def get(self, request):
        sessions = ChatSession.objects.filter(
            tenant=request.user.tenant
        ).values('id', 'created_at')
        return Response(list(sessions))


class ChatSessionDetailView(APIView):
    permission_classes = [IsTenantMember]

    def get(self, request, pk):
        try:
            session = ChatSession.objects.get(id=pk, tenant=request.user.tenant)
            messages = session.messages.values('id', 'role', 'content', 'sources', 'created_at')
            return Response({'session_id': str(session.id), 'messages': list(messages)})
        except ChatSession.DoesNotExist:
            return Response({'error': 'غير موجود'}, status=status.HTTP_404_NOT_FOUND)