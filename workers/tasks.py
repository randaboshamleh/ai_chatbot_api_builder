import logging
import os
import tempfile

from celery import shared_task
from django.apps import apps

from core.rag.document_processor import DocumentProcessor
from core.rag.vector_store import TenantVectorStore

logger = logging.getLogger(__name__)



@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name='workers.tasks.process_document',
)
def process_document_task(self, document_id: str):
    """
    Task غير متزامن لمعالجة الوثيقة وفهرستها
    يُنفَّذ بواسطة Celery Worker
    """
    Document = apps.get_model('documents', 'Document')
    DocumentChunk = apps.get_model('documents', 'DocumentChunk')
    
    try:
        document = Document.objects.select_related('tenant').get(id=document_id)
        document.status = 'processing'
        document.save(update_fields=['status'])
        
        logger.info(f"Processing document: {document.title} for tenant: {document.tenant.name}")

        # تحميل الملف من التخزين
        with tempfile.NamedTemporaryFile(
            suffix=f"_{document.original_filename}",
            delete=False
        ) as tmp_file:
            for chunk in document.file.chunks():
                tmp_file.write(chunk)
            tmp_path = tmp_file.name

        try:
            # معالجة الوثيقة
            processor = DocumentProcessor(chunk_size=1000, chunk_overlap=200)
            chunks, processing_time = processor.process(
                file_path=tmp_path,
                file_type=document.file_type,
                metadata={
                    'source': document.original_filename,
                    'title': document.title,
                    'tags': document.tags,
                },
            )

            # حذف الـ chunks القديمة من PostgreSQL وChromaDB
            DocumentChunk.objects.filter(document=document).delete()
            vector_store = TenantVectorStore(str(document.tenant.id))
            try:
                vector_store.delete_document(str(document.id))
            except Exception:
                pass

            # فهرسة في ChromaDB
            vector_ids = vector_store.add_documents(chunks, str(document.id))

            # حفظ الـ chunks في PostgreSQL
            chunk_objects = [
                DocumentChunk(
                    document=document,
                    vector_id=vector_ids[i],
                    chunk_index=i,
                    content=chunk.page_content,
                    metadata=chunk.metadata,
                )
                for i, chunk in enumerate(chunks)
            ]
            DocumentChunk.objects.bulk_create(chunk_objects, batch_size=500)

            # تحديث حالة الوثيقة
            document.status = 'indexed'
            document.chunk_count = len(chunks)
            document.processing_time = processing_time
            document.save(update_fields=['status', 'chunk_count', 'processing_time'])
            
            logger.info(
                f"Document {document_id} indexed successfully. "
                f"Chunks: {len(chunks)}, Time: {processing_time:.2f}s"
            )

        finally:
            os.unlink(tmp_path)  # حذف الملف المؤقت

    except Exception as exc:
        logger.error(f"Error processing document {document_id}: {exc}")
        Document.objects.filter(id=document_id).update(
            status='failed',
            error_message=str(exc)[:1000],
        )
        raise self.retry(exc=exc)
