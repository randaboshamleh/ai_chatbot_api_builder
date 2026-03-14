import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser


class Tenant(models.Model):
    """
    يمثل كل شركة مستأجر منفصل مع عزل تام للبيانات
    """
    PLAN_CHOICES = [
        ('free', 'Free'),
        ('pro', 'Pro'),
        ('enterprise', 'Enterprise'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    subdomain = models.SlugField(unique=True)
    logo = models.ImageField(upload_to='tenants/logos/', blank=True, null=True)
    contact_email = models.EmailField(blank=True)
    api_key = models.CharField(max_length=64, unique=True)
    
    # Plan & Limits
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default='free')
    max_documents = models.IntegerField(default=100)
    max_queries_per_day = models.IntegerField(default=1000)
    max_users = models.IntegerField(default=5)
    
    # Status
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tenants'
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.api_key:
            import secrets
            self.api_key = secrets.token_urlsafe(48)
        super().save(*args, **kwargs)


class TenantUser(AbstractUser):
    """مستخدمو كل شركة"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        Tenant, 
        on_delete=models.CASCADE, 
        related_name='users',
        null=True
    )
    role = models.CharField(
        max_length=20,
        choices=[
            ('owner', 'Owner'),
            ('admin', 'Admin'),
            ('member', 'Member'),
            ('viewer', 'Viewer'),
        ],
        default='member'
    )
    
    class Meta:
        db_table = 'tenant_users'
    
    def is_admin_or_owner(self):
        return self.role in ['owner', 'admin']
    
    
class TenantChannel(models.Model):
    CHANNEL_TYPES = [
        ('web', 'Web Widget'),
        ('telegram', 'Telegram Bot'),
        ('whatsapp', 'WhatsApp Business'),
    ]
    INPUT_MODES = [
        ('text', 'Text Only'),
        ('voice', 'Voice Only'),
        ('both', 'Text & Voice'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='channels')
    channel_type = models.CharField(max_length=20, choices=CHANNEL_TYPES)
    is_active = models.BooleanField(default=False)
    input_mode = models.CharField(max_length=10, choices=INPUT_MODES, default='both')

    # Telegram
    telegram_token = models.CharField(max_length=200, blank=True)
    telegram_webhook_set = models.BooleanField(default=False)

    # WhatsApp
    whatsapp_token = models.CharField(max_length=500, blank=True)
    whatsapp_phone_id = models.CharField(max_length=100, blank=True)
    whatsapp_verify_token = models.CharField(max_length=100, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tenant_channels'
        unique_together = ['tenant', 'channel_type']

    def __str__(self):
        return f"{self.tenant.name} - {self.channel_type}"    