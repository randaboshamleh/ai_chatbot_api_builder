import hashlib
import logging

from django.conf import settings
from django.db import transaction
from rest_framework import status, generics
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.documents.models import Document
from apps.documents.serializers import DocumentSerializer, DocumentUploadSerializer
from apps.documents.permissions import IsTenantMember, IsTenantAdminOrOwner
from core.rag.vector_store import TenantVectorStore

logger = logging.getLogger(__name__)


class DocumentUploadView(APIView):
    """
    رفع وثيقة جديدة مع بدء المعالجة الفورية
    """
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsTenantAdminOrOwner]

    @staticmethod
    def _estimate_wait_seconds(file_size: int) -> int:
        size_mb = file_size / (1024 * 1024)
        if size_mb <= 2:
            return 60
        if size_mb <= 10:
            return 3 * 60
        if size_mb <= 25:
            return 6 * 60
        return 10 * 60

    def post(self, request):
        serializer = DocumentUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        file = request.FILES['file']
        tenant = request.user.tenant

        # التحقق من حجم الملف
        if file.size > settings.MAX_FILE_SIZE:
            return Response(
                {'error': f'حجم الملف يتجاوز الحد المسموح ({settings.MAX_FILE_SIZE // (1024*1024)}MB)'},
                status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            )

        # التحقق من نوع الملف
        if settings.ALLOWED_DOCUMENT_TYPES and file.content_type not in settings.ALLOWED_DOCUMENT_TYPES:
            return Response(
                {'error': f'نوع الملف غير مدعوم: {file.content_type}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # التحقق من حدود الاشتراك
        current_count = Document.objects.filter(
            tenant=tenant, 
            status__in=['indexed', 'processing']
        ).count()
        if current_count >= tenant.max_documents:
            return Response(
                {'error': 'تجاوزت الحد الأقصى للوثائق في خطتك'},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        # حساب checksum بشكل تدريجي لتقليل استهلاك الذاكرة مع الملفات الكبيرة.
        sha256 = hashlib.sha256()
        for chunk in file.chunks():
            sha256.update(chunk)
        checksum = sha256.hexdigest()
        file.seek(0)
        
        # التحقق من عدم التكرار
        if Document.objects.filter(tenant=tenant, checksum=checksum).exists():
            return Response(
                {'error': 'هذه الوثيقة مرفوعة مسبقاً'},
                status=status.HTTP_409_CONFLICT,
            )

        # إنشاء سجل الوثيقة
        document = Document.objects.create(
            tenant=tenant,
            uploaded_by=request.user,
            title=serializer.validated_data.get('title', file.name),
            original_filename=file.name,
            file=file,
            file_type=file.content_type,
            file_size=file.size,
            checksum=checksum,
            tags=serializer.validated_data.get('tags', []),
            metadata=serializer.validated_data.get('metadata', {}),
        )

        # بدء المعالجة بشكل غير متزامن
        def enqueue_processing():
            try:
                from workers.tasks import process_document_task
                process_document_task.delay(str(document.id))
            except Exception:
                # Task dispatch failure should never break upload response.
                logger.exception("Failed to enqueue document processing task for document %s", document.id)

        transaction.on_commit(enqueue_processing)

        response_data = DocumentSerializer(document).data
        response_data.update(
            {
                'status_message': 'queued_for_indexing',
                'estimated_wait_seconds': self._estimate_wait_seconds(file.size),
                'poll_interval_seconds': 5,
            }
        )

        return Response(response_data, status=status.HTTP_202_ACCEPTED)


class DocumentListView(generics.ListAPIView):
    """قائمة وثائق الشركة"""
    serializer_class = DocumentSerializer

    def get_queryset(self):
        return Document.objects.filter(
            tenant=self.request.user.tenant
        ).select_related('uploaded_by')


class DocumentDeleteView(generics.DestroyAPIView):
    """حذف وثيقة مع بياناتها من ChromaDB"""
    permission_classes = [IsTenantAdminOrOwner]

    def get_queryset(self):
        return Document.objects.filter(tenant=self.request.user.tenant)

    def perform_destroy(self, instance):
        # حذف من ChromaDB أولاً
        vector_store = TenantVectorStore(str(instance.tenant.id))
        vector_store.delete_document(str(instance.id))
        
        # حذف من PostgreSQL
        instance.delete()
        logger.info(f"Document {instance.id} deleted completely")


class DocumentStatusView(APIView):
    permission_classes = [IsTenantMember]

    def get(self, request, pk):
        try:
            doc = Document.objects.get(id=pk, tenant=request.user.tenant)
            wait_hint = DocumentUploadView._estimate_wait_seconds(doc.file_size)
            return Response(
                {
                    'id': str(doc.id),
                    'status': doc.status,
                    'status_message': (
                        'indexing_complete'
                        if doc.status == 'indexed'
                        else 'indexing_failed'
                        if doc.status == 'failed'
                        else 'indexing_in_progress'
                    ),
                    'estimated_wait_seconds': wait_hint if doc.status in ['pending', 'processing'] else 0,
                    'processing_time': doc.processing_time,
                    'chunk_count': doc.chunk_count,
                    'error_message': doc.error_message or None,
                    'updated_at': doc.updated_at,
                }
            )
        except Document.DoesNotExist:
            return Response({'error': 'غير موجود'}, status=status.HTTP_404_NOT_FOUND)        
