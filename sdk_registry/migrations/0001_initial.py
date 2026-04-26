# Generated for Auth Platform v30 SDK registry foundation.

import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="IntegrationGuide",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("slug", models.SlugField(max_length=120, unique=True)),
                ("title", models.CharField(max_length=200)),
                ("audience", models.CharField(choices=[("web", "Web"), ("android", "Android"), ("windows", "Windows"), ("backend", "Backend"), ("admin", "Admin")], max_length=32)),
                ("summary", models.TextField(blank=True)),
                ("content_markdown", models.TextField()),
                ("is_published", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["audience", "title"]},
        ),
        migrations.CreateModel(
            name="SdkCompatibilityMatrix",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("sdk_platform", models.CharField(max_length=32)),
                ("sdk_version", models.CharField(max_length=40)),
                ("api_version", models.CharField(default="v1", max_length=40)),
                ("min_server_version", models.CharField(blank=True, max_length=40)),
                ("max_server_version", models.CharField(blank=True, max_length=40)),
                ("supports_pkce", models.BooleanField(default=True)),
                ("supports_refresh_rotation", models.BooleanField(default=True)),
                ("supports_step_up", models.BooleanField(default=True)),
                ("supports_passkeys", models.BooleanField(default=False)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["sdk_platform", "-created_at"], "unique_together": {("sdk_platform", "sdk_version", "api_version")}},
        ),
        migrations.CreateModel(
            name="SdkTelemetryEvent",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("organization_id", models.UUIDField(blank=True, null=True)),
                ("application_id", models.CharField(blank=True, max_length=120)),
                ("platform", models.CharField(max_length=32)),
                ("sdk_version", models.CharField(blank=True, max_length=40)),
                ("event_type", models.CharField(choices=[("install", "Install"), ("auth_started", "Auth Started"), ("auth_succeeded", "Auth Succeeded"), ("auth_failed", "Auth Failed"), ("token_refresh", "Token Refresh"), ("error", "Error")], max_length=40)),
                ("event_name", models.CharField(blank=True, max_length=160)),
                ("user_agent", models.TextField(blank=True)),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="SdkRelease",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("platform", models.CharField(choices=[("typescript", "TypeScript / JavaScript"), ("android_kotlin", "Android Kotlin"), ("windows_dotnet", "Windows .NET"), ("cli", "Command Line"), ("docs", "Documentation")], max_length=32)),
                ("version", models.CharField(max_length=40)),
                ("status", models.CharField(choices=[("draft", "Draft"), ("published", "Published"), ("deprecated", "Deprecated"), ("revoked", "Revoked")], default="draft", max_length=20)),
                ("download_url", models.URLField(blank=True)),
                ("checksum_sha256", models.CharField(blank=True, max_length=128)),
                ("minimum_api_version", models.CharField(default="v1", max_length=40)),
                ("release_notes", models.TextField(blank=True)),
                ("breaking_changes", models.TextField(blank=True)),
                ("published_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["platform", "-created_at"], "unique_together": {("platform", "version")}},
        ),
    ]
