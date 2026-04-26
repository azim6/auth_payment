# Generated for django-auth-platform v6 hardening layer.
import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("accounts", "0005_auditlog_servicecredential_oauthtokenactivity"),
    ]
    operations = [
        migrations.CreateModel(
            name="AuthSessionDevice",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("session_key_hash", models.CharField(db_index=True, max_length=128)),
                ("label", models.CharField(blank=True, max_length=120)),
                ("user_agent", models.TextField(blank=True)),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("last_seen_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("revoked_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="auth_session_devices", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-last_seen_at"]},
        ),
        migrations.CreateModel(
            name="RefreshTokenFamily",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("jti", models.CharField(max_length=255, unique=True)),
                ("parent_jti", models.CharField(blank=True, max_length=255)),
                ("client_id", models.CharField(blank=True, max_length=120)),
                ("user_agent", models.TextField(blank=True)),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("expires_at", models.DateTimeField()),
                ("revoked_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("last_seen_at", models.DateTimeField(blank=True, null=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="refresh_token_families", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddIndex(model_name="authsessiondevice", index=models.Index(fields=["user", "last_seen_at"], name="accounts_aut_user_id_0f4b9a_idx")),
        migrations.AddIndex(model_name="authsessiondevice", index=models.Index(fields=["session_key_hash"], name="accounts_aut_session_3e0f1a_idx")),
        migrations.AddIndex(model_name="authsessiondevice", index=models.Index(fields=["revoked_at"], name="accounts_aut_revoked_c52c6a_idx")),
        migrations.AddIndex(model_name="refreshtokenfamily", index=models.Index(fields=["user", "created_at"], name="accounts_ref_user_id_a3e673_idx")),
        migrations.AddIndex(model_name="refreshtokenfamily", index=models.Index(fields=["jti"], name="accounts_ref_jti_7b6f11_idx")),
        migrations.AddIndex(model_name="refreshtokenfamily", index=models.Index(fields=["client_id", "created_at"], name="accounts_ref_client__eeb9d0_idx")),
        migrations.AddIndex(model_name="refreshtokenfamily", index=models.Index(fields=["expires_at"], name="accounts_ref_expires_d16d71_idx")),
        migrations.AddIndex(model_name="refreshtokenfamily", index=models.Index(fields=["revoked_at"], name="accounts_ref_revoked_6d85be_idx")),
    ]
