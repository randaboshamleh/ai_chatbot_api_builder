from apps.documents.models import Document

docs = Document.objects.all().order_by('-created_at')
print("=== All Documents ===")
print(f"Total: {docs.count()}")
print()
for doc in docs[:5]:  # Show last 5
    print(f"Title: {doc.title}")
    print(f"Status: {doc.status}")
    print(f"Tenant: {doc.tenant.name}")
    print(f"Chunks: {doc.chunks_count}")
    print(f"Created: {doc.created_at}")
    print("---")
