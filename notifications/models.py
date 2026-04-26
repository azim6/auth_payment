from __future__ import annotations

import hashlib
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class NotificationChannel(models.TextChoices):
    EMAIL = "email", _("Email")
    SMS = "sms", _("SMS")
    PUSH = "push", _("Push")
    IN_APP = "in_app", _("In-app")
    WEBHOOK = "webhook", _("Webhook")


class NotificationPriority(models.TextChoices):
    LOW = "low", _("Low")
    NORMAL = "normal", _("Normal")
    HIGH = "high", _("High")
    CRITICAL = "critical", _("Critical")


class NotificationProvider(models.Model):
    """Logical delivery provider configuration. Secrets live in environment/provider vaults, not this table."""

    class Status(models.TextChoices):
        ACTIVE = "active", _("Active")
        DISABLED = "disabled", _("Disabled")
        DEGRADED = "degraded", _("Degraded")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120)
    channel = models.CharField(max_length=16, choices=NotificationChannel.choices)
    provider_code = models.CharField(max_length=80, help_text="ses, sendgrid, twilio, fcm, apns, internal, etc.")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    priority = models.PositiveSmallIntegerField(default=100)
    config = models.JSONField(default=dict, blank=True, help_text="Non-secret provider metadata only.")
    last_success_at = models.DateTimeField(null=True, blank=True)
    last_failure_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["channel", "priority", "name"]
        indexes = [models.Index(fields=["channel", "status", "priority"])]

    def __str__(self) -> str:
        return f"{self.channel}:{self.provider_code}:{self.name}"


class NotificationTemplate(models.Model):
    """Versioned template for account, billing, security, compliance, and app events."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    key = models.SlugField(max_length=120)
    channel = models.CharField(max_length=16, choices=NotificationChannel.choices)
    locale = models.CharField(max_length=16, default="en")
    project = models.ForeignKey("billing.Project", on_delete=models.PROTECT, null=True, blank=True, related_name="notification_templates")
    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, null=True, blank=True, related_name="notification_templates")
    version = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    subject_template = models.CharField(max_length=240, blank=True)
    body_template = models.TextField()
    html_template = models.TextField(blank=True)
    variables_schema = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="notification_templates_created")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("key", "channel", "locale", "version", "organization")]
        ordering = ["key", "channel", "locale", "-version"]
        indexes = [models.Index(fields=["key", "channel", "locale", "is_active"]), models.Index(fields=["organization", "is_active"])]

    def __str__(self) -> str:
        tenant = self.organization.slug if self.organization_id else "global"
        return f"{tenant}:{self.key}:{self.channel}:v{self.version}"


class NotificationPreference(models.Model):
    """Per-user notification preferences, optionally scoped to an organization tenant."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notification_preferences")
    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, null=True, blank=True, related_name="notification_preferences")
    topic = models.CharField(max_length=120, help_text="security, billing, product, marketing, compliance, etc.")
    channel = models.CharField(max_length=16, choices=NotificationChannel.choices)
    enabled = models.BooleanField(default=True)
    locale = models.CharField(max_length=16, default="en")
    timezone = models.CharField(max_length=64, default="UTC")
    quiet_hours_start = models.TimeField(null=True, blank=True)
    quiet_hours_end = models.TimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("user", "organization", "topic", "channel")]
        ordering = ["user", "organization", "topic", "channel"]
        indexes = [models.Index(fields=["user", "topic", "channel"]), models.Index(fields=["organization", "topic"])]

    def __str__(self) -> str:
        scope = self.organization.slug if self.organization_id else "global"
        return f"{self.user_id}:{scope}:{self.topic}:{self.channel}"


class DevicePushToken(models.Model):
    """Hashed device token registry for Android, Windows, and web push clients."""

    class Platform(models.TextChoices):
        ANDROID = "android", _("Android")
        WINDOWS = "windows", _("Windows")
        WEB = "web", _("Web")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="push_tokens")
    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, null=True, blank=True, related_name="push_tokens")
    platform = models.CharField(max_length=16, choices=Platform.choices)
    device_id = models.CharField(max_length=160, blank=True)
    token_prefix = models.CharField(max_length=24)
    token_hash = models.CharField(max_length=128, unique=True)
    is_active = models.BooleanField(default=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "platform", "is_active"]), models.Index(fields=["token_prefix"])]

    def __str__(self) -> str:
        return f"{self.user_id}:{self.platform}:{self.token_prefix}"

    @staticmethod
    def hash_token(raw_token: str) -> str:
        return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    @classmethod
    def prefix_token(cls, raw_token: str) -> str:
        return raw_token[:20]

    def revoke(self) -> None:
        if self.revoked_at is None:
            self.is_active = False
            self.revoked_at = timezone.now()
            self.save(update_fields=["is_active", "revoked_at", "updated_at"])


class NotificationEvent(models.Model):
    """Durable event produced by auth, billing, security, compliance, ops, and project apps."""

    class Status(models.TextChoices):
        RECEIVED = "received", _("Received")
        QUEUED = "queued", _("Queued")
        DISPATCHED = "dispatched", _("Dispatched")
        SKIPPED = "skipped", _("Skipped")
        FAILED = "failed", _("Failed")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, null=True, blank=True, related_name="notification_events")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name="notification_events")
    project = models.ForeignKey("billing.Project", on_delete=models.PROTECT, null=True, blank=True, related_name="notification_events")
    event_type = models.CharField(max_length=120)
    topic = models.CharField(max_length=120, default="product")
    priority = models.CharField(max_length=16, choices=NotificationPriority.choices, default=NotificationPriority.NORMAL)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.RECEIVED)
    idempotency_key = models.CharField(max_length=160, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    scheduled_for = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="notification_events_created")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["idempotency_key"], condition=~models.Q(idempotency_key=""), name="uniq_notification_idempotency_key")]
        indexes = [models.Index(fields=["organization", "event_type"]), models.Index(fields=["user", "topic"]), models.Index(fields=["status", "scheduled_for"])]

    def __str__(self) -> str:
        return f"{self.event_type}:{self.status}"


class NotificationDelivery(models.Model):
    """Per-channel delivery attempt state for a NotificationEvent."""

    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        SENT = "sent", _("Sent")
        SKIPPED = "skipped", _("Skipped")
        FAILED = "failed", _("Failed")
        DEAD = "dead", _("Dead-lettered")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(NotificationEvent, on_delete=models.CASCADE, related_name="deliveries")
    template = models.ForeignKey(NotificationTemplate, on_delete=models.SET_NULL, null=True, blank=True, related_name="deliveries")
    provider = models.ForeignKey(NotificationProvider, on_delete=models.SET_NULL, null=True, blank=True, related_name="deliveries")
    channel = models.CharField(max_length=16, choices=NotificationChannel.choices)
    recipient = models.CharField(max_length=320)
    recipient_hash = models.CharField(max_length=128, db_index=True)
    subject = models.CharField(max_length=240, blank=True)
    body = models.TextField(blank=True)
    html_body = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    attempt_count = models.PositiveIntegerField(default=0)
    max_attempts = models.PositiveIntegerField(default=5)
    next_attempt_at = models.DateTimeField(default=timezone.now)
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    provider_message_id = models.CharField(max_length=160, blank=True)
    error_message = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["channel", "status", "next_attempt_at"]), models.Index(fields=["event", "status"]), models.Index(fields=["recipient_hash"])]

    def __str__(self) -> str:
        return f"{self.channel}:{self.status}:{self.recipient_hash[:8]}"


class NotificationSuppression(models.Model):
    """Suppression list for unsubscribes, hard bounces, complaints, and admin blocks."""

    class Reason(models.TextChoices):
        UNSUBSCRIBE = "unsubscribe", _("Unsubscribe")
        BOUNCE = "bounce", _("Hard bounce")
        COMPLAINT = "complaint", _("Complaint")
        ADMIN_BLOCK = "admin_block", _("Admin block")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    channel = models.CharField(max_length=16, choices=NotificationChannel.choices)
    recipient_hash = models.CharField(max_length=128)
    reason = models.CharField(max_length=24, choices=Reason.choices)
    note = models.TextField(blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="notification_suppressions_created")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("channel", "recipient_hash", "reason")]
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["channel", "recipient_hash"]), models.Index(fields=["expires_at"])]

    @property
    def is_active(self) -> bool:
        return self.expires_at is None or timezone.now() < self.expires_at
