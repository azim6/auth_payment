import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class SdkRelease(models.Model):
    PLATFORM_TYPES = [
        ("typescript", "TypeScript / JavaScript"),
        ("android_kotlin", "Android Kotlin"),
        ("windows_dotnet", "Windows .NET"),
        ("cli", "Command Line"),
        ("docs", "Documentation"),
    ]
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("published", "Published"),
        ("deprecated", "Deprecated"),
        ("revoked", "Revoked"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    platform = models.CharField(max_length=32, choices=PLATFORM_TYPES)
    version = models.CharField(max_length=40)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    download_url = models.URLField(blank=True)
    checksum_sha256 = models.CharField(max_length=128, blank=True)
    minimum_api_version = models.CharField(max_length=40, default="v1")
    release_notes = models.TextField(blank=True)
    breaking_changes = models.TextField(blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("platform", "version")]
        ordering = ["platform", "-created_at"]

    def publish(self):
        self.status = "published"
        self.published_at = self.published_at or timezone.now()
        self.save(update_fields=["status", "published_at", "updated_at"])

    def __str__(self):
        return f"{self.platform} {self.version} ({self.status})"


class IntegrationGuide(models.Model):
    AUDIENCE_CHOICES = [
        ("web", "Web"),
        ("android", "Android"),
        ("windows", "Windows"),
        ("backend", "Backend"),
        ("admin", "Admin"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(max_length=120, unique=True)
    title = models.CharField(max_length=200)
    audience = models.CharField(max_length=32, choices=AUDIENCE_CHOICES)
    summary = models.TextField(blank=True)
    content_markdown = models.TextField()
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["audience", "title"]

    def __str__(self):
        return self.title


class SdkCompatibilityMatrix(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sdk_platform = models.CharField(max_length=32)
    sdk_version = models.CharField(max_length=40)
    api_version = models.CharField(max_length=40, default="v1")
    min_server_version = models.CharField(max_length=40, blank=True)
    max_server_version = models.CharField(max_length=40, blank=True)
    supports_pkce = models.BooleanField(default=True)
    supports_refresh_rotation = models.BooleanField(default=True)
    supports_step_up = models.BooleanField(default=True)
    supports_passkeys = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("sdk_platform", "sdk_version", "api_version")]
        ordering = ["sdk_platform", "-created_at"]

    def __str__(self):
        return f"{self.sdk_platform} {self.sdk_version} -> {self.api_version}"


class SdkTelemetryEvent(models.Model):
    EVENT_TYPES = [
        ("install", "Install"),
        ("auth_started", "Auth Started"),
        ("auth_succeeded", "Auth Succeeded"),
        ("auth_failed", "Auth Failed"),
        ("token_refresh", "Token Refresh"),
        ("error", "Error"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization_id = models.UUIDField(null=True, blank=True)
    application_id = models.CharField(max_length=120, blank=True)
    platform = models.CharField(max_length=32)
    sdk_version = models.CharField(max_length=40, blank=True)
    event_type = models.CharField(max_length=40, choices=EVENT_TYPES)
    event_name = models.CharField(max_length=160, blank=True)
    user_agent = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.platform}:{self.event_type}:{self.created_at:%Y-%m-%d}"
