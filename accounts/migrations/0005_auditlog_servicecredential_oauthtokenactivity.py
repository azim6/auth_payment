# Generated for django-auth-platform v5.

import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0004_oauthclient_authorizationcode"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AuditLog",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("category", models.CharField(choices=[("auth", "Authentication"), ("account", "Account"), ("mfa", "MFA"), ("oauth", "OAuth/OIDC"), ("service", "Service credential"), ("admin", "Admin")], max_length=24)),
                ("action", models.CharField(max_length=80)),
                ("outcome", models.CharField(choices=[("success", "Success"), ("failure", "Failure"), ("denied", "Denied")], default="success", max_length=16)),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("user_agent", models.TextField(blank=True)),
                ("request_id", models.CharField(blank=True, max_length=100)),
                ("client_id", models.CharField(blank=True, max_length=120)),
                ("subject_user_id", models.UUIDField(blank=True, null=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("actor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="audit_events", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["category", "action"], name="accounts_au_categor_07b9b0_idx"),
                    models.Index(fields=["outcome"], name="accounts_au_outcome_75a0c7_idx"),
                    models.Index(fields=["actor", "created_at"], name="accounts_au_actor_i_c4f0bb_idx"),
                    models.Index(fields=["client_id", "created_at"], name="accounts_au_client__77a668_idx"),
                    models.Index(fields=["created_at"], name="accounts_au_created_c8f778_idx"),
                ],
            },
        ),
        migrations.CreateModel(
            name="ServiceCredential",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=150)),
                ("key_prefix", models.CharField(max_length=16, unique=True)),
                ("key_hash", models.CharField(max_length=256)),
                ("scopes", models.CharField(default="users:read tokens:introspect", max_length=255)),
                ("is_active", models.BooleanField(default=True)),
                ("last_used_at", models.DateTimeField(blank=True, null=True)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("owner", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="service_credentials", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "indexes": [
                    models.Index(fields=["key_prefix"], name="accounts_se_key_pre_a987b9_idx"),
                    models.Index(fields=["is_active"], name="accounts_se_is_acti_e72a87_idx"),
                    models.Index(fields=["expires_at"], name="accounts_se_expires_bf0d71_idx"),
                    models.Index(fields=["created_at"], name="accounts_se_created_5a9f27_idx"),
                ],
            },
        ),
        migrations.CreateModel(
            name="OAuthTokenActivity",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("jti", models.CharField(max_length=255, unique=True)),
                ("token_type", models.CharField(choices=[("access", "Access token"), ("refresh", "Refresh token"), ("id", "ID token"), ("service", "Service token")], max_length=16)),
                ("scope", models.CharField(blank=True, max_length=255)),
                ("expires_at", models.DateTimeField()),
                ("revoked_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("last_seen_at", models.DateTimeField(blank=True, null=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("client", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="token_activity", to="accounts.oauthclient")),
                ("service_credential", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="token_activity", to="accounts.servicecredential")),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="oauth_token_activity", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "indexes": [
                    models.Index(fields=["jti"], name="accounts_oa_jti_ea7bb9_idx"),
                    models.Index(fields=["token_type"], name="accounts_oa_token_t_04148a_idx"),
                    models.Index(fields=["client", "created_at"], name="accounts_oa_client__07d68d_idx"),
                    models.Index(fields=["service_credential", "created_at"], name="accounts_oa_service_02c1be_idx"),
                    models.Index(fields=["user", "created_at"], name="accounts_oa_user_id_954e0c_idx"),
                    models.Index(fields=["expires_at"], name="accounts_oa_expires_d5fb46_idx"),
                    models.Index(fields=["revoked_at"], name="accounts_oa_revoked_2c742c_idx"),
                ],
            },
        ),
    ]
