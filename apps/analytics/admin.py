from django.contrib import admin
from apps.analytics.models import QueryLog


@admin.register(QueryLog)
class QueryLogAdmin(admin.ModelAdmin):
    list_display = ['tenant', 'query_preview', 'response_time', 'chunks_used', 'created_at']
    list_filter = ['tenant', 'created_at']
    search_fields = ['query', 'tenant__name']
    readonly_fields = ['id', 'created_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('id', 'tenant', 'user')
        }),
        ('Query', {
            'fields': ('query',)
        }),
        ('Response', {
            'fields': ('answer', 'chunks_used', 'response_time')
        }),
        ('Sources', {
            'fields': ('sources',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        }),
    )
    
    def query_preview(self, obj):
        return obj.query[:50] + '...' if len(obj.query) > 50 else obj.query
    query_preview.short_description = 'Query'
