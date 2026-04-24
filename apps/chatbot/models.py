import uuid
from django.db import models
from apps.tenants.models import Tenant, TenantUser


class ChatSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    user = models.ForeignKey(TenantUser, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'chat_sessions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', '-created_at'], name='chat_sess_tenant_created_idx'),
        ]


class ChatMessage(models.Model):
    ROLE_CHOICES = [('user', 'User'), ('assistant', 'Assistant')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    sources = models.JSONField(default=list)
    metadata = models.JSONField(default=dict)  # ← أضف هاد
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'chat_messages'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['session', 'created_at'], name='chat_msg_session_created_idx'),
            models.Index(fields=['role', 'created_at'], name='chat_msg_role_created_idx'),
        ]
