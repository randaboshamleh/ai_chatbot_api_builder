import logging
import os
import tempfile

from celery import shared_task
from django.apps import apps
from django.conf import settings

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name='workers.tasks.process_document',
)
def process_document_task(self, document_id: str):
    Document = apps.get_model('documents', 'Document')
    DocumentChunk = apps.get_model('documents', 'DocumentChunk')

    try:
        # Lazy imports: keep Django startup/migrations resilient even if optional
        # RAG deps are temporarily unavailable in the environment.
        from core.rag.document_processor import DocumentProcessor
        from core.rag.vector_store import TenantVectorStore

        document = Document.objects.select_related('tenant').get(id=document_id)
        document.status = 'processing'
        document.save(update_fields=['status'])

        logger.info(f"Processing document: {document.title} for tenant: {document.tenant.name}")

        with tempfile.NamedTemporaryFile(suffix=f"_{document.original_filename}", delete=False) as tmp_file:
            for chunk in document.file.chunks():
                tmp_file.write(chunk)
            tmp_path = tmp_file.name

        try:
            chunk_size = max(
                400,
                int(os.getenv('DOCUMENT_CHUNK_SIZE', getattr(settings, 'DOCUMENT_CHUNK_SIZE', 1400))),
            )
            chunk_overlap = max(
                0,
                int(os.getenv('DOCUMENT_CHUNK_OVERLAP', getattr(settings, 'DOCUMENT_CHUNK_OVERLAP', 100))),
            )
            if chunk_overlap >= chunk_size:
                chunk_overlap = max(0, chunk_size // 4)

            processor = DocumentProcessor(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
            chunks, processing_time = processor.process(
                file_path=tmp_path,
                file_type=document.file_type,
                metadata={
                    'source': document.original_filename,
                    'title': document.title,
                    'tags': document.tags,
                },
            )

            DocumentChunk.objects.filter(document=document).delete()
            vector_store = TenantVectorStore(str(document.tenant.id))
            try:
                vector_store.delete_document(str(document.id))
            except Exception:
                pass

            vector_ids = vector_store.add_documents(chunks, str(document.id))

            chunk_objects = [
                DocumentChunk(
                    document=document,
                    vector_id=vector_ids[i],
                    chunk_index=i,
                    content=chunk.page_content.replace('\x00', ''),
                    metadata=chunk.metadata,
                )
                for i, chunk in enumerate(chunks)
            ]
            batch_size = max(
                100,
                int(
                    os.getenv(
                        'DOCUMENT_BULK_CREATE_BATCH_SIZE',
                        getattr(settings, 'DOCUMENT_BULK_CREATE_BATCH_SIZE', 1000),
                    )
                ),
            )
            DocumentChunk.objects.bulk_create(chunk_objects, batch_size=batch_size)

            document.status = 'indexed'
            document.chunk_count = len(chunks)
            document.processing_time = processing_time
            document.save(update_fields=['status', 'chunk_count', 'processing_time'])

            logger.info(f"Document {document_id} indexed. Chunks: {len(chunks)}, Time: {processing_time:.2f}s")

            # Trigger hierarchical summary generation asynchronously
            generate_summaries_task.delay(str(document.tenant.id), document_id)

        finally:
            os.unlink(tmp_path)

    except Exception as exc:
        logger.error(f"Error processing document {document_id}: {exc}")
        Document.objects.filter(id=document_id).update(
            status='failed',
            error_message=str(exc)[:1000],
        )
        if not self.request.is_eager:
            try:
                raise self.retry(exc=exc)
            except Exception:
                pass


@shared_task(
    bind=True,
    max_retries=1,
    name='workers.tasks.generate_summaries',
    time_limit=600,
    soft_time_limit=570,
)
def generate_summaries_task(self, tenant_id: str, document_id: str = None):
    """
    Generate hierarchical summaries for a tenant's knowledge base.
    - Section summaries per category
    - Global summary from all section summaries
    Stores them in ChromaDB via vector_store.add_summaries()
    """
    from apps.documents.models import DocumentChunk
    from apps.tenants.models import Tenant
    from core.rag.pipeline import RAGPipeline

    try:
        tenant = Tenant.objects.get(id=tenant_id)
        pipeline = RAGPipeline(tenant=tenant)
        vector_store = pipeline.vector_store

        # Gather all chunks for this tenant from DB
        qs = DocumentChunk.objects.filter(document__tenant=tenant).values('content', 'metadata')
        if document_id:
            qs = qs.filter(document_id=document_id)

        # Group by category
        category_texts: dict = {}
        for row in qs:
            cat = row['metadata'].get('category', 'general') if row['metadata'] else 'general'
            category_texts.setdefault(cat, []).append(row['content'])

        if not category_texts:
            logger.info(f"No chunks found for tenant {tenant_id}, skipping summaries.")
            return

        summaries_to_store = []
        section_summary_texts = []

        # Level 2: Section summaries
        for cat, texts in category_texts.items():
            combined = "\n\n".join(texts)[:3000]
            summary_text = pipeline.generate_summary(combined)
            if summary_text:
                summaries_to_store.append(
                    {
                        'text': summary_text,
                        'level': 'section_summary',
                        'category': cat,
                        'document_id': document_id or 'all',
                    }
                )
                section_summary_texts.append(f"{cat}: {summary_text}")
                logger.info(f"Generated section summary for category '{cat}'")

        # Level 1: Global summary from section summaries
        if section_summary_texts:
            global_input = "\n\n".join(section_summary_texts)[:3000]
            global_summary = pipeline.generate_summary(global_input)
            if global_summary:
                summaries_to_store.append(
                    {
                        'text': global_summary,
                        'level': 'global_summary',
                        'category': 'all',
                        'document_id': document_id or 'all',
                    }
                )
                logger.info(f"Generated global summary for tenant {tenant_id}")

        if summaries_to_store:
            vector_store.add_summaries(summaries_to_store)
            logger.info(f"Stored {len(summaries_to_store)} summaries for tenant {tenant_id}")

    except Exception as exc:
        logger.error(f"generate_summaries_task error for tenant {tenant_id}: {exc}")
        if not self.request.is_eager:
            try:
                raise self.retry(exc=exc)
            except Exception:
                pass


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    name='workers.tasks.process_telegram_message',
    time_limit=300,
    soft_time_limit=270,
)
def process_telegram_message(self, tenant_id: str, chat_id, text: str, token: str):
    from apps.chatbot.channel_processors import process_telegram_message_sync, send_telegram_message

    try:
        process_telegram_message_sync(tenant_id, chat_id, text, token)
    except Exception as exc:
        logger.error(f"process_telegram_message error: {exc}")
        send_telegram_message(token, chat_id, "عذراً، حدث خطأ أثناء معالجة سؤالك. حاول مرة أخرى.")
        if not self.request.is_eager:
            try:
                raise self.retry(exc=exc)
            except Exception:
                pass


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    name='workers.tasks.process_whatsapp_message',
    time_limit=300,
    soft_time_limit=270,
)
def process_whatsapp_message(self, tenant_id: str, phone: str, text: str, token: str, phone_id: str):
    from apps.chatbot.channel_processors import process_whatsapp_message_sync, send_whatsapp_message

    try:
        process_whatsapp_message_sync(tenant_id, phone, text, token, phone_id)
    except Exception as exc:
        logger.error(f"process_whatsapp_message error: {exc}")
        send_whatsapp_message(token, phone_id, phone, "عذراً، حدث خطأ أثناء معالجة سؤالك. حاول مرة أخرى.")
        if not self.request.is_eager:
            try:
                raise self.retry(exc=exc)
            except Exception:
                pass
