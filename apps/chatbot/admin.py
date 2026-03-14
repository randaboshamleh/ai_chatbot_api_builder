from django.contrib import admin
from apps.chatbot.models import ChatSession, ChatMessage


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'tenant', 'message_count', 'created_at']
    list_filter = ['tenant', 'created_at']
    search_fields = ['id', 'tenant__name']
    readonly_fields = ['id', 'created_at']
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('id', 'tenant', 'user')
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        }),
    )
    
    def message_count(self, obj):
        return obj.messages.count()
    message_count.short_description = 'Messages'


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ['session', 'role', 'content_preview', 'sources_count', 'created_at']
    list_filter = ['role', 'session__tenant', 'created_at']
    search_fields = ['content', 'session__id']
    readonly_fields = ['id', 'created_at']
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('id', 'session', 'role')
        }),
        ('Content', {
            'fields': ('content',)
        }),
        ('Sources', {
            'fields': ('sources',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        }),
    )
    
    def content_preview(self, obj):
        return obj.content[:100] + '...' if len(obj.content) > 100 else obj.content
    content_preview.short_description = 'Content'
    
    def sources_count(self, obj):
        return len(obj.sources) if obj.sources else 0
    sources_count.short_description = 'Sources'
