from django.contrib import admin
from apps.tenants.models import Tenant, TenantUser, TenantChannel


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ['name', 'subdomain', 'plan', 'is_active', 'created_at']
    list_filter = ['plan', 'is_active', 'created_at']
    search_fields = ['name', 'subdomain', 'contact_email']
    readonly_fields = ['id', 'api_key', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('id', 'name', 'subdomain', 'logo', 'contact_email', 'is_active')
        }),
        ('Plan & Limits', {
            'fields': ('plan', 'max_documents', 'max_queries_per_day', 'max_users')
        }),
        ('API', {
            'fields': ('api_key',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(TenantUser)
class TenantUserAdmin(admin.ModelAdmin):
    list_display = ['email', 'tenant', 'role', 'is_active', 'date_joined']
    list_filter = ['role', 'is_active', 'tenant', 'date_joined']
    search_fields = ['email', 'first_name', 'last_name']
    readonly_fields = ['id', 'date_joined', 'last_login']
    
    fieldsets = (
        ('User Info', {
            'fields': ('id', 'email', 'first_name', 'last_name', 'is_active')
        }),
        ('Tenant & Role', {
            'fields': ('tenant', 'role')
        }),
        ('Permissions', {
            'fields': ('is_staff', 'is_superuser', 'groups', 'user_permissions')
        }),
        ('Timestamps', {
            'fields': ('date_joined', 'last_login')
        }),
    )


@admin.register(TenantChannel)
class TenantChannelAdmin(admin.ModelAdmin):
    list_display = ['tenant', 'channel_type', 'is_active', 'input_mode', 'created_at']
    list_filter = ['channel_type', 'is_active', 'input_mode', 'created_at']
    search_fields = ['tenant__name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('id', 'tenant', 'channel_type', 'is_active', 'input_mode')
        }),
        ('Telegram Config', {
            'fields': ('telegram_token', 'telegram_webhook_url'),
            'classes': ('collapse',)
        }),
        ('WhatsApp Config', {
            'fields': ('whatsapp_token', 'whatsapp_phone_id', 'whatsapp_verify_token'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
