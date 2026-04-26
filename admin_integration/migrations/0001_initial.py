import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(name='AdminApiScope', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('code', models.CharField(max_length=120, unique=True)),
            ('title', models.CharField(max_length=180)),
            ('description', models.TextField(blank=True)),
            ('risk', models.CharField(choices=[('low','Low'),('medium','Medium'),('high','High'),('critical','Critical')], default='medium', max_length=16)),
            ('requires_two_person_approval', models.BooleanField(default=False)),
            ('enabled', models.BooleanField(default=True)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
            ('updated_at', models.DateTimeField(auto_now=True)),
        ], options={'ordering': ['code']}),
        migrations.CreateModel(name='AdminServiceCredential', fields=[
            ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
            ('name', models.CharField(max_length=180)),
            ('key_prefix', models.CharField(max_length=20, unique=True)),
            ('key_hash', models.CharField(max_length=256)),
            ('signing_key_id', models.CharField(max_length=64, unique=True)),
            ('signing_secret', models.CharField(help_text='Use encrypted/KMS storage in production.', max_length=256)),
            ('scopes', models.CharField(default='admin:readiness admin:read', max_length=1000)),
            ('allowed_ips', models.JSONField(blank=True, default=list)),
            ('is_active', models.BooleanField(default=True)),
            ('expires_at', models.DateTimeField(blank=True, null=True)),
            ('last_used_at', models.DateTimeField(blank=True, null=True)),
            ('rotated_at', models.DateTimeField(blank=True, null=True)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
            ('updated_at', models.DateTimeField(auto_now=True)),
            ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_admin_service_credentials', to=settings.AUTH_USER_MODEL)),
        ], options={'ordering': ['name']}),
        migrations.CreateModel(name='AdminApiContractEndpoint', fields=[
            ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
            ('domain', models.CharField(choices=[('auth','Auth'),('billing','Billing'),('tenancy','Tenancy'),('security','Security'),('ops','Operations'),('admin_console','Admin Console'),('portal','Customer Portal'),('observability','Observability'),('other','Other')], max_length=32)),
            ('method', models.CharField(max_length=12)),
            ('path', models.CharField(max_length=300)),
            ('required_scope', models.CharField(blank=True, max_length=120)),
            ('description', models.TextField(blank=True)),
            ('stable', models.BooleanField(default=True)),
            ('enabled', models.BooleanField(default=True)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
            ('updated_at', models.DateTimeField(auto_now=True)),
        ], options={'ordering': ['domain','path','method']}),
        migrations.CreateModel(name='AdminRequestAudit', fields=[
            ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
            ('key_prefix', models.CharField(blank=True, max_length=20)),
            ('method', models.CharField(max_length=12)),
            ('path', models.CharField(max_length=600)),
            ('query_string_hash', models.CharField(blank=True, max_length=64)),
            ('body_hash', models.CharField(blank=True, max_length=64)),
            ('nonce', models.CharField(blank=True, max_length=128)),
            ('timestamp', models.CharField(blank=True, max_length=64)),
            ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
            ('user_agent', models.CharField(blank=True, max_length=500)),
            ('decision', models.CharField(choices=[('allowed','Allowed'),('denied','Denied'),('unsigned','Unsigned'),('error','Error')], default='unsigned', max_length=16)),
            ('status_code', models.PositiveIntegerField(blank=True, null=True)),
            ('latency_ms', models.PositiveIntegerField(blank=True, null=True)),
            ('error', models.CharField(blank=True, max_length=500)),
            ('metadata', models.JSONField(blank=True, default=dict)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
            ('credential', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='request_audits', to='admin_integration.adminservicecredential')),
        ], options={'ordering': ['-created_at']}),
        migrations.CreateModel(name='AdminIntegrationReadinessSnapshot', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('status', models.CharField(max_length=32)),
            ('checks', models.JSONField(default=list)),
            ('metadata', models.JSONField(blank=True, default=dict)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
            ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
        ], options={'ordering': ['-created_at']}),
        migrations.AddConstraint(model_name='adminapicontractendpoint', constraint=models.UniqueConstraint(fields=('method','path'), name='unique_admin_contract_method_path')),
    ]
