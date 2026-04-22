# Generated migration for adding web channel support

from django.db import migrations


def create_web_channels(apps, schema_editor):
    """Create web channel for all existing tenants"""
    Tenant = apps.get_model('tenants', 'Tenant')
    TenantChannel = apps.get_model('tenants', 'TenantChannel')
    
    for tenant in Tenant.objects.all():
        TenantChannel.objects.get_or_create(
            tenant=tenant,
            channel_type='web',
            defaults={
                'is_active': True,
                'input_mode': 'text',
            }
        )


class Migration(migrations.Migration):

    dependencies = [
        ('tenants', '0004_alter_tenant_logo'),
    ]

    operations = [
        migrations.RunPython(create_web_channels, reverse_code=migrations.RunPython.noop),
    ]
