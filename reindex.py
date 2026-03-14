import django
django.setup()
from apps.documents.models import Document, DocumentChunk
from core.rag.document_processor import DocumentProcessor
from core.rag.vector_store import TenantVectorStore
import tempfile, os

for d in Document.objects.all():
    try:
        tmp = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
        for c in d.file.chunks():
            tmp.write(c)
        tmp.close()
        processor = DocumentProcessor(chunk_size=1000, chunk_overlap=200)
        chunks, pt = processor.process(
            file_path=tmp.name,
            file_type=d.file_type,
            metadata={'source': d.original_filename, 'title': d.title, 'tags': d.tags}
        )
        DocumentChunk.objects.filter(document=d).delete()
        store = TenantVectorStore(str(d.tenant.id))
        store.delete_document(str(d.id))
        store.add_documents(chunks, str(d.id))
        d.status = 'indexed'
        d.chunk_count = len(chunks)
        d.save(update_fields=['status', 'chunk_count'])
        print('OK:', d.id, len(chunks))
        os.unlink(tmp.name)
    except Exception as e:
        import traceback
        print('ERROR:', d.id, e)
        traceback.print_exc()

from apps.tenants.models import Tenant
t = Tenant.objects.first()
store = TenantVectorStore(str(t.id))
print('Total chunks:', store.collection.count())