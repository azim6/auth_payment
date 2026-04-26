# Generated for django-auth-platform v7 privacy/compliance workflow.

import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0006_sessiondevice_refreshtokenfamily"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="PrivacyPreference",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("analytics_consent", models.BooleanField(default=False)),
                ("marketing_email_consent", models.BooleanField(default=False)),
                ("product_email_consent", models.BooleanField(default=True)),
                ("profile_discoverable", models.BooleanField(default=True)),
                ("data_processing_region", models.CharField(default="default", max_length=32)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="privacy_preferences", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="UserConsent",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("consent_type", models.CharField(choices=[("terms", "Terms of service"), ("privacy", "Privacy policy"), ("marketing", "Marketing communications"), ("analytics", "Analytics")], max_length=32)),
                ("version", models.CharField(max_length=64)),
                ("granted", models.BooleanField(default=True)),
                ("source", models.CharField(choices=[("web", "Web"), ("android", "Android"), ("windows", "Windows"), ("api", "API"), ("admin", "Admin")], default="api", max_length=32)),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("user_agent", models.TextField(blank=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="consents", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="DataExportRequest",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("processing", "Processing"), ("ready", "Ready"), ("failed", "Failed"), ("expired", "Expired")], default="pending", max_length=16)),
                ("format", models.CharField(default="json", max_length=16)),
                ("download_url", models.URLField(blank=True)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("error", models.TextField(blank=True)),
                ("requested_ip", models.GenericIPAddressField(blank=True, null=True)),
                ("requested_user_agent", models.TextField(blank=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="data_export_requests", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="AccountDeletionRequest",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("confirmed", "Confirmed"), ("cancelled", "Cancelled"), ("completed", "Completed")], default="pending", max_length=16)),
                ("reason", models.TextField(blank=True)),
                ("requested_ip", models.GenericIPAddressField(blank=True, null=True)),
                ("requested_user_agent", models.TextField(blank=True)),
                ("confirm_before", models.DateTimeField()),
                ("scheduled_for", models.DateTimeField()),
                ("confirmed_at", models.DateTimeField(blank=True, null=True)),
                ("cancelled_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="deletion_requests", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddIndex(model_name="privacypreference", index=models.Index(fields=["user"], name="accounts_pr_user_id_a1b2c3_idx")),
        migrations.AddIndex(model_name="privacypreference", index=models.Index(fields=["updated_at"], name="accounts_pr_updated_d4e5f6_idx")),
        migrations.AddIndex(model_name="userconsent", index=models.Index(fields=["user", "consent_type", "created_at"], name="accounts_uc_user_con_a1b2_idx")),
        migrations.AddIndex(model_name="userconsent", index=models.Index(fields=["consent_type", "version"], name="accounts_uc_con_ver_c3d4_idx")),
        migrations.AddIndex(model_name="userconsent", index=models.Index(fields=["created_at"], name="accounts_uc_created_e5f6_idx")),
        migrations.AddIndex(model_name="dataexportrequest", index=models.Index(fields=["user", "created_at"], name="accounts_de_user_cre_a1b2_idx")),
        migrations.AddIndex(model_name="dataexportrequest", index=models.Index(fields=["status", "created_at"], name="accounts_de_status_c3d4_idx")),
        migrations.AddIndex(model_name="dataexportrequest", index=models.Index(fields=["expires_at"], name="accounts_de_expires_e5f6_idx")),
        migrations.AddIndex(model_name="accountdeletionrequest", index=models.Index(fields=["user", "status"], name="accounts_ad_user_sta_a1b2_idx")),
        migrations.AddIndex(model_name="accountdeletionrequest", index=models.Index(fields=["status", "scheduled_for"], name="accounts_ad_status_c3d4_idx")),
        migrations.AddIndex(model_name="accountdeletionrequest", index=models.Index(fields=["confirm_before"], name="accounts_ad_confirm_e5f6_idx")),
    ]
