from django.contrib import admin
from apps.documents.models import Document, DocumentChunk


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ['title', 'tenant', 'status', 'file_type', 'file_size_mb', 'chunk_count', 'created_at']
    list_filter = ['status', 'file_type', 'tenant', 'created_at']
    search_fields = ['title', 'original_filename', 'tenant__name']
    readonly_fields = ['id', 'checksum', 'created_at', 'updated_at', 'processing_time']
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('id', 'tenant', 'uploaded_by', 'title', 'original_filename')
        }),
        ('File Info', {
            'fields': ('file', 'file_type', 'file_size', 'checksum')
        }),
        ('Processing', {
            'fields': ('status', 'chunk_count', 'processing_time', 'error_message')
        }),
        ('Metadata', {
            'fields': ('tags', 'metadata'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def file_size_mb(self, obj):
        return f"{obj.file_size / (1024*1024):.2f} MB"
    file_size_mb.short_description = 'File Size'


@admin.register(DocumentChunk)
class DocumentChunkAdmin(admin.ModelAdmin):
    list_display = ['document', 'chunk_index', 'content_preview', 'created_at']
    list_filter = ['document__tenant', 'created_at']
    search_fields = ['document__title', 'content']
    readonly_fields = ['id', 'vector_id', 'created_at']
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('id', 'document', 'vector_id', 'chunk_index')
        }),
        ('Content', {
            'fields': ('content',)
        }),
        ('Metadata', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        }),
    )
    
    def content_preview(self, obj):
        return obj.content[:100] + '...' if len(obj.content) > 100 else obj.content
    content_preview.short_description = 'Content Preview'
