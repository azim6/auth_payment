# Generated for django-auth-platform v25.
import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("accounts", "0009_rbac_policies"),
    ]

    operations = [
        migrations.CreateModel(
            name="PortalProfileSettings",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("display_name", models.CharField(blank=True, max_length=160)),
                ("preferred_locale", models.CharField(choices=[("en", "English"), ("ar", "Arabic"), ("auto", "Auto")], default="auto", max_length=12)),
                ("timezone", models.CharField(default="UTC", max_length=80)),
                ("theme", models.CharField(choices=[("system", "System"), ("light", "Light"), ("dark", "Dark")], default="system", max_length=16)),
                ("marketing_opt_in", models.BooleanField(default=False)),
                ("security_emails_enabled", models.BooleanField(default=True)),
                ("product_emails_enabled", models.BooleanField(default=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="portal_profile_settings", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="PortalOrganizationBookmark",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("label", models.CharField(blank=True, max_length=120)),
                ("sort_order", models.PositiveIntegerField(default=100)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="portal_bookmarks", to="accounts.organization")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="portal_org_bookmarks", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["sort_order", "organization__name"]},
        ),
        migrations.CreateModel(
            name="PortalApiKey",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=160)),
                ("key_prefix", models.CharField(db_index=True, max_length=24)),
                ("key_hash", models.CharField(max_length=256)),
                ("scopes", models.TextField(blank=True, help_text="Space-delimited scopes granted to this key.")),
                ("status", models.CharField(choices=[("active", "Active"), ("revoked", "Revoked"), ("expired", "Expired")], default="active", max_length=16)),
                ("allowed_origins", models.JSONField(blank=True, default=list)),
                ("allowed_ips", models.JSONField(blank=True, default=list)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("last_used_at", models.DateTimeField(blank=True, null=True)),
                ("revoked_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("organization", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="portal_api_keys", to="accounts.organization")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="portal_api_keys", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="PortalSupportRequest",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("category", models.CharField(choices=[("account", "Account"), ("security", "Security"), ("billing", "Billing"), ("organization", "Organization"), ("integration", "Integration"), ("privacy", "Privacy"), ("other", "Other")], default="other", max_length=24)),
                ("status", models.CharField(choices=[("open", "Open"), ("waiting_on_customer", "Waiting on customer"), ("waiting_on_support", "Waiting on support"), ("resolved", "Resolved"), ("closed", "Closed")], default="open", max_length=32)),
                ("subject", models.CharField(max_length=200)),
                ("message", models.TextField()),
                ("priority", models.CharField(default="normal", max_length=16)),
                ("related_object_type", models.CharField(blank=True, max_length=80)),
                ("related_object_id", models.CharField(blank=True, max_length=128)),
                ("operator_task_id", models.UUIDField(blank=True, help_text="Optional admin_console.OperatorTask link created by support escalation.", null=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("resolved_at", models.DateTimeField(blank=True, null=True)),
                ("organization", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="portal_support_requests", to="accounts.organization")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="portal_support_requests", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="PortalActivityLog",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("domain", models.CharField(choices=[("auth", "Auth"), ("security", "Security"), ("billing", "Billing"), ("organization", "Organization"), ("api", "API"), ("privacy", "Privacy")], max_length=24)),
                ("event_type", models.CharField(max_length=120)),
                ("title", models.CharField(max_length=200)),
                ("summary", models.TextField(blank=True)),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("user_agent", models.TextField(blank=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("organization", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="portal_activity_logs", to="accounts.organization")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="portal_activity_logs", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddConstraint(
            model_name="portalorganizationbookmark",
            constraint=models.UniqueConstraint(fields=("user", "organization"), name="unique_portal_org_bookmark"),
        ),
        migrations.AddIndex(model_name="portalprofilesettings", index=models.Index(fields=["user"], name="customer_po_user_id_445cba_idx")),
        migrations.AddIndex(model_name="portalorganizationbookmark", index=models.Index(fields=["user", "sort_order"], name="customer_po_user_id_e47dc9_idx")),
        migrations.AddIndex(model_name="portalapikey", index=models.Index(fields=["user", "status"], name="customer_po_user_id_095ad4_idx")),
        migrations.AddIndex(model_name="portalapikey", index=models.Index(fields=["organization", "status"], name="customer_po_organiz_0ab376_idx")),
        migrations.AddIndex(model_name="portalapikey", index=models.Index(fields=["key_prefix"], name="customer_po_key_pre_3d83b8_idx")),
        migrations.AddIndex(model_name="portalsupportrequest", index=models.Index(fields=["user", "status"], name="customer_po_user_id_6f24e1_idx")),
        migrations.AddIndex(model_name="portalsupportrequest", index=models.Index(fields=["organization", "status"], name="customer_po_organiz_ba6c3d_idx")),
        migrations.AddIndex(model_name="portalsupportrequest", index=models.Index(fields=["category", "status"], name="customer_po_categor_c0b8a2_idx")),
        migrations.AddIndex(model_name="portalactivitylog", index=models.Index(fields=["user", "domain", "created_at"], name="customer_po_user_id_c78528_idx")),
        migrations.AddIndex(model_name="portalactivitylog", index=models.Index(fields=["organization", "domain", "created_at"], name="customer_po_organiz_2d7cc2_idx")),
        migrations.AddIndex(model_name="portalactivitylog", index=models.Index(fields=["event_type"], name="customer_po_event_t_1f3547_idx")),
    ]
