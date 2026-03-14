# Generated migration

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('tenants', '0001_initial'),
        ('analytics', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='querylog',
            name='question',
        ),
        migrations.RemoveField(
            model_name='querylog',
            name='was_answered',
        ),
        migrations.AddField(
            model_name='querylog',
            name='query',
            field=models.TextField(default=''),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='querylog',
            name='answer',
            field=models.TextField(blank=True, default=''),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='querylog',
            name='sources',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name='querylog',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='querylog',
            name='tenant',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='query_logs', to='tenants.tenant'),
        ),
        migrations.AddIndex(
            model_name='querylog',
            index=models.Index(fields=['tenant', '-created_at'], name='query_logs_tenant__idx'),
        ),
    ]
