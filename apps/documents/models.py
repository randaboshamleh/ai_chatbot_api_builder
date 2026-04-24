import uuid
from django.db import models
from apps.tenants.models import Tenant, TenantUser


class Document(models.Model):
    """
    وثيقة مرفوعة من قِبَل شركة
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('indexed', 'Indexed'),
        ('failed', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='documents')
    uploaded_by = models.ForeignKey(TenantUser, on_delete=models.SET_NULL, null=True)
    
    # معلومات الملف
    title = models.CharField(max_length=500)
    original_filename = models.CharField(max_length=500)
    file = models.FileField(upload_to='documents/%Y/%m/')
    file_type = models.CharField(max_length=100)
    file_size = models.BigIntegerField()
    
    # checksum للتحقق من سلامة الملف
    checksum = models.CharField(max_length=64)
    
    # حالة المعالجة
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    error_message = models.TextField(blank=True)
    
    # إحصائيات
    chunk_count = models.IntegerField(default=0)
    processing_time = models.FloatField(null=True)
    
    # Metadata
    metadata = models.JSONField(default=dict)
    tags = models.JSONField(default=list)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'documents'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'status'], name='doc_tenant_status_idx'),
            models.Index(fields=['tenant', '-created_at'], name='doc_tenant_created_idx'),
        ]
    
    def __str__(self):
        return f"{self.tenant.name} - {self.title}"


class DocumentChunk(models.Model):
    """تمثيل كل chunk من الوثيقة بعد التقطيع"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='chunks')
    
    # مرجع في ChromaDB
    vector_id = models.CharField(max_length=100, unique=True)
    
    chunk_index = models.IntegerField()
    content = models.TextField()
    metadata = models.JSONField(default=dict)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'document_chunks'
        ordering = ['chunk_index']
        indexes = [
            models.Index(fields=['document', 'chunk_index'], name='doc_chunk_doc_chunk_idx'),
        ]
