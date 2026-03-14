# apps/analytics/models.py
import uuid
from django.db import models
from apps.tenants.models import Tenant


class DailyStats(models.Model):
    """إحصائيات يومية لكل شركة"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    date = models.DateField()
    
    total_queries = models.IntegerField(default=0)
    total_documents = models.IntegerField(default=0)
    indexed_documents = models.IntegerField(default=0)
    active_sessions = models.IntegerField(default=0)
    avg_response_time = models.FloatField(default=0.0)
    
    class Meta:
        db_table = 'daily_stats'
        unique_together = ['tenant', 'date']
        ordering = ['-date']


class QueryLog(models.Model):
    """سجل كل سؤال مع وقت الاستجابة"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='query_logs')
    user = models.ForeignKey('tenants.TenantUser', on_delete=models.SET_NULL, null=True, blank=True)
    query = models.TextField()
    answer = models.TextField(blank=True)
    response_time = models.FloatField()
    chunks_used = models.IntegerField(default=0)
    sources = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'query_logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', '-created_at']),
        ]