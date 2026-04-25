import logging
import os
import tempfile
import threading

from django.http import StreamingHttpResponse
from rest_framework import status
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.chatbot.models import ChatMessage, ChatSession
from apps.chatbot.preprocessing import preprocess_user_text
from apps.chatbot.serializers import ChatQuerySerializer
from apps.chatbot.services import (
    get_or_create_session,
    get_today_query_count,
    run_query,
    run_stream_query,
    store_query_log,
    tenant_has_indexed_documents,
)
from apps.documents.permissions import IsTenantMember

logger = logging.getLogger(__name__)

_WHISPER_MODEL = None
_WHISPER_MODEL_LOCK = threading.Lock()


def _get_whisper_model():
    global _WHISPER_MODEL
    if _WHISPER_MODEL is not None:
        return _WHISPER_MODEL

    with _WHISPER_MODEL_LOCK:
        if _WHISPER_MODEL is None:
            import whisper

            _WHISPER_MODEL = whisper.load_model("base")

    return _WHISPER_MODEL


class ChatQueryView(APIView):
    permission_classes = [IsTenantMember]

    def post(self, request):
        tenant = request.user.tenant

        serializer = ChatQuerySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        question = preprocess_user_text(
            serializer.validated_data['question'],
            max_length=ChatQuerySerializer().fields['question'].max_length,
        )
        if not question:
            return Response({'error': 'السؤال مطلوب'}, status=status.HTTP_400_BAD_REQUEST)
        stream = serializer.validated_data.get('stream', False)
        session_id = serializer.validated_data.get('session_id')

        if get_today_query_count(tenant) >= tenant.max_queries_per_day:
            return Response({'error': 'تجاوزت الحد اليومي'}, status=status.HTTP_429_TOO_MANY_REQUESTS)

        if not tenant_has_indexed_documents(tenant):
            return Response({'error': 'لا توجد وثائق مفهرسة بعد'}, status=status.HTTP_404_NOT_FOUND)

        session = get_or_create_session(tenant, session_id=session_id)

        ChatMessage.objects.create(session=session, role='user', content=question)

        try:
            if stream:
                return self._stream_response(tenant, question, session)

            result, response_time = run_query(tenant, question)

            ChatMessage.objects.create(
                session=session,
                role='assistant',
                content=result['answer'],
                sources=result['sources'],
            )

            store_query_log(
                tenant=tenant,
                user=request.user,
                question=question,
                answer=result['answer'],
                response_time=response_time,
                chunks_used=result['chunks_used'],
                sources=result['sources'],
            )

            return Response(
                {
                    'session_id': str(session.id),
                    'answer': result['answer'],
                    'sources': result['sources'],
                    'chunks_used': result['chunks_used'],
                }
            )

        except Exception as exc:
            logger.error("RAG error: %s", exc)
            return Response({'error': 'حدث خطأ أثناء معالجة السؤال'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _stream_response(self, tenant, question, session):
        def event_stream():
            full_response = []
            try:
                result = run_stream_query(tenant, question)
                for token in result['answer']:
                    full_response.append(token)
                    yield f"data: {token}\n\n"

                ChatMessage.objects.create(
                    session=session,
                    role='assistant',
                    content=''.join(full_response),
                    sources=result.get('sources', []),
                )
                yield "data: [DONE]\n\n"
            except Exception as exc:
                logger.error("Streaming error: %s", exc)
                yield f"data: [ERROR] {str(exc)}\n\n"

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
            model = _get_whisper_model()

            with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as temp_file:
                for chunk in audio_file.chunks():
                    temp_file.write(chunk)
                temp_path = temp_file.name

            try:
                transcription = model.transcribe(temp_path)
            finally:
                os.unlink(temp_path)

            question = preprocess_user_text(transcription['text'])
            if not question:
                return Response({'error': 'ما تم التعرف على الصوت'}, status=status.HTTP_400_BAD_REQUEST)

            result, _response_time = run_query(tenant, question)

            return Response(
                {
                    'question': question,
                    'answer': result['answer'],
                    'sources': result['sources'],
                }
            )
        except Exception as exc:
            logger.error("Voice query error: %s", exc)
            return Response({'error': 'خطأ في معالجة الصوت'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ChatSessionListView(APIView):
    permission_classes = [IsTenantMember]

    def get(self, request):
        sessions = ChatSession.objects.filter(tenant=request.user.tenant).values('id', 'created_at')
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
