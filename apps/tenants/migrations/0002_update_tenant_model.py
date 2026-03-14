# Generated migration

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tenants', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='tenant',
            old_name='slug',
            new_name='subdomain',
        ),
        migrations.RenameField(
            model_name='tenant',
            old_name='subscription_plan',
            new_name='plan',
        ),
        migrations.RemoveField(
            model_name='tenant',
            name='chatbot_name',
        ),
        migrations.RemoveField(
            model_name='tenant',
            name='chatbot_language',
        ),
        migrations.RemoveField(
            model_name='tenant',
            name='system_prompt',
        ),
        migrations.AddField(
            model_name='tenant',
            name='logo',
            field=models.ImageField(blank=True, null=True, upload_to='tenants/logos/'),
        ),
        migrations.AddField(
            model_name='tenant',
            name='contact_email',
            field=models.EmailField(blank=True, max_length=254),
        ),
        migrations.AddField(
            model_name='tenant',
            name='max_users',
            field=models.IntegerField(default=5),
        ),
    ]
