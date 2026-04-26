from __future__ import annotations

import secrets
import uuid

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class DeveloperApplication(models.Model):
    """First-party project app registration for web, Android, Windows, service, and CLI clients."""

    class AppType(models.TextChoices):
        WEB = "web", _("Web")
        ANDROID = "android", _("Android")
        WINDOWS = "windows", _("Windows desktop")
        SERVICE = "service", _("Service/server")
        CLI = "cli", _("CLI")

    class Environment(models.TextChoices):
        DEVELOPMENT = "development", _("Development")
        STAGING = "staging", _("Staging")
        PRODUCTION = "production", _("Production")

    class Status(models.TextChoices):
        ACTIVE = "active", _("Active")
        DISABLED = "disabled", _("Disabled")
        SUSPENDED = "suspended", _("Suspended")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, related_name="developer_applications")
    project = models.ForeignKey("billing.Project", on_delete=models.PROTECT, null=True, blank=True, related_name="developer_applications")
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=100)
    app_type = models.CharField(max_length=24, choices=AppType.choices)
    environment = models.CharField(max_length=24, choices=Environment.choices, default=Environment.PRODUCTION)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.ACTIVE)
    client_id = models.CharField(max_length=64, unique=True, editable=False)
    client_secret_hash = models.CharField(max_length=256, blank=True)
    client_secret_prefix = models.CharField(max_length=16, blank=True)
    redirect_uris = models.JSONField(default=list, blank=True)
    allowed_origins = models.JSONField(default=list, blank=True)
    allowed_package_names = models.JSONField(default=list, blank=True)
    allowed_bundle_ids = models.JSONField(default=list, blank=True)
    allowed_scopes = models.TextField(blank=True, help_text="Space-delimited scopes allowed for this app.")
    token_ttl_seconds = models.PositiveIntegerField(default=3600)
    require_pkce = models.BooleanField(default=True)
    require_mfa = models.BooleanField(default=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="developer_applications_created")
    last_used_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("organization", "slug", "environment")]
        ordering = ["organization", "project__code", "name"]
        indexes = [
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["client_id"]),
            models.Index(fields=["app_type", "environment"]),
        ]

    def __str__(self) -> str:
        return f"{self.organization.slug}:{self.slug}:{self.environment}"

    @property
    def scope_set(self) -> set[str]:
        return {scope for scope in self.allowed_scopes.split() if scope}

    @classmethod
    def generate_client_id(cls) -> str:
        return f"app_{secrets.token_urlsafe(24)}"

    @classmethod
    def generate_client_secret(cls) -> str:
        return f"appsec_{secrets.token_urlsafe(36)}"

    def set_client_secret(self, raw_secret: str) -> None:
        self.client_secret_hash = make_password(raw_secret)
        self.client_secret_prefix = raw_secret[:14]

    def check_client_secret(self, raw_secret: str) -> bool:
        return bool(self.client_secret_hash) and check_password(raw_secret, self.client_secret_hash)

    def mark_used(self) -> None:
        self.last_used_at = timezone.now()
        self.save(update_fields=["last_used_at", "updated_at"])


class SDKTokenPolicy(models.Model):
    """Controls which SDK/client token patterns are allowed for an application."""

    class Platform(models.TextChoices):
        WEB = "web", _("Web")
        ANDROID = "android", _("Android")
        WINDOWS = "windows", _("Windows")
        SERVER = "server", _("Server")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(DeveloperApplication, on_delete=models.CASCADE, related_name="sdk_token_policies")
    platform = models.CharField(max_length=24, choices=Platform.choices)
    allow_public_client = models.BooleanField(default=True)
    require_device_binding = models.BooleanField(default=False)
    require_attestation = models.BooleanField(default=False)
    max_token_ttl_seconds = models.PositiveIntegerField(default=3600)
    allowed_scopes = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("application", "platform")]
        ordering = ["application", "platform"]

    def __str__(self) -> str:
        return f"{self.application.client_id}:{self.platform}"


class WebhookSubscription(models.Model):
    """Outbound webhook subscription for first-party projects consuming auth/billing events."""

    class Status(models.TextChoices):
        ACTIVE = "active", _("Active")
        PAUSED = "paused", _("Paused")
        DISABLED = "disabled", _("Disabled")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, related_name="webhook_subscriptions")
    application = models.ForeignKey(DeveloperApplication, on_delete=models.CASCADE, related_name="webhook_subscriptions")
    name = models.CharField(max_length=160)
    target_url = models.URLField(max_length=500)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    event_types = models.JSONField(default=list)
    secret_hash = models.CharField(max_length=256, blank=True)
    secret_prefix = models.CharField(max_length=16, blank=True)
    max_attempts = models.PositiveIntegerField(default=8)
    last_success_at = models.DateTimeField(null=True, blank=True)
    last_failure_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="webhook_subscriptions_created")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["organization", "name"]
        indexes = [models.Index(fields=["organization", "status"]), models.Index(fields=["application", "status"])]

    def __str__(self) -> str:
        return f"{self.organization.slug}:{self.name}"

    @classmethod
    def generate_secret(cls) -> str:
        return f"whsec_{secrets.token_urlsafe(40)}"

    def set_secret(self, raw_secret: str) -> None:
        self.secret_hash = make_password(raw_secret)
        self.secret_prefix = raw_secret[:14]

    def check_secret(self, raw_secret: str) -> bool:
        return bool(self.secret_hash) and check_password(raw_secret, self.secret_hash)


class WebhookDelivery(models.Model):
    """Durable outbound webhook delivery log with replay state."""

    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        DELIVERED = "delivered", _("Delivered")
        FAILED = "failed", _("Failed")
        DEAD = "dead", _("Dead-lettered")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subscription = models.ForeignKey(WebhookSubscription, on_delete=models.CASCADE, related_name="deliveries")
    event_id = models.UUIDField(default=uuid.uuid4, editable=False)
    event_type = models.CharField(max_length=120)
    payload = models.JSONField(default=dict)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    attempt_count = models.PositiveIntegerField(default=0)
    next_attempt_at = models.DateTimeField(default=timezone.now)
    response_status_code = models.PositiveIntegerField(null=True, blank=True)
    response_body = models.TextField(blank=True)
    error_message = models.TextField(blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["subscription", "status"]), models.Index(fields=["event_type", "status"]), models.Index(fields=["next_attempt_at"])]

    def __str__(self) -> str:
        return f"{self.event_type}:{self.status}"


class IntegrationAuditEvent(models.Model):
    """Audit trail for developer platform configuration and outbound integrations."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, related_name="integration_audit_events")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="integration_audit_events")
    application = models.ForeignKey(DeveloperApplication, on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_events")
    action = models.CharField(max_length=120)
    target_type = models.CharField(max_length=80, blank=True)
    target_id = models.CharField(max_length=120, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["organization", "created_at"]), models.Index(fields=["action"])]

    def __str__(self) -> str:
        return f"{self.organization.slug}:{self.action}:{self.created_at:%Y-%m-%d}"
