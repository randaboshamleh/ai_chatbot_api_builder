from rest_framework import serializers
from .models import Document


class DocumentSerializer(serializers.ModelSerializer):
    uploaded_by_username = serializers.CharField(source='uploaded_by.username', read_only=True)

    class Meta:
        model = Document
        fields = [
            'id', 'title', 'original_filename', 'file_type',
            'file_size', 'status', 'chunk_count', 'processing_time',
            'error_message', 'tags', 'metadata', 'uploaded_by_username',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'status', 'chunk_count', 'processing_time', 'error_message',
            'created_at', 'updated_at',
        ]


class DocumentUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
    title = serializers.CharField(max_length=500, required=False)
    tags = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list,
    )

    ALLOWED_TYPES = [
        'application/pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'text/plain',
        'text/csv',
        'application/vnd.ms-excel',
    ]

    def validate_file(self, file):
        if file.content_type not in self.ALLOWED_TYPES:
            raise serializers.ValidationError("نوع الملف غير مدعوم. الأنواع المسموحة: PDF, DOCX, XLSX, TXT,CSV")
        if file.size > 100 * 1024 * 1024:
            raise serializers.ValidationError("حجم الملف يتجاوز 100MB")
        return file
