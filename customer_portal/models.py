import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class PortalProfileSettings(models.Model):
    """User-owned self-service preferences for the customer portal."""

    class Locale(models.TextChoices):
        EN = "en", _("English")
        AR = "ar", _("Arabic")
        AUTO = "auto", _("Auto")

    class Theme(models.TextChoices):
        SYSTEM = "system", _("System")
        LIGHT = "light", _("Light")
        DARK = "dark", _("Dark")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="portal_profile_settings")
    display_name = models.CharField(max_length=160, blank=True)
    preferred_locale = models.CharField(max_length=12, choices=Locale.choices, default=Locale.AUTO)
    timezone = models.CharField(max_length=80, default="UTC")
    theme = models.CharField(max_length=16, choices=Theme.choices, default=Theme.SYSTEM)
    marketing_opt_in = models.BooleanField(default=False)
    security_emails_enabled = models.BooleanField(default=True)
    product_emails_enabled = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["user"])]

    def __str__(self):
        return f"portal-settings:{self.user_id}"


class PortalOrganizationBookmark(models.Model):
    """Pinned organization/workspace for portal navigation."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="portal_org_bookmarks")
    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, related_name="portal_bookmarks")
    label = models.CharField(max_length=120, blank=True)
    sort_order = models.PositiveIntegerField(default=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "organization__name"]
        constraints = [models.UniqueConstraint(fields=["user", "organization"], name="unique_portal_org_bookmark")]
        indexes = [models.Index(fields=["user", "sort_order"])]

    def __str__(self):
        return f"bookmark:{self.user_id}:{self.organization_id}"


class PortalApiKey(models.Model):
    """Customer-created API key metadata. Raw key is displayed once by the service layer."""

    class Status(models.TextChoices):
        ACTIVE = "active", _("Active")
        REVOKED = "revoked", _("Revoked")
        EXPIRED = "expired", _("Expired")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="portal_api_keys")
    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, null=True, blank=True, related_name="portal_api_keys")
    name = models.CharField(max_length=160)
    key_prefix = models.CharField(max_length=24, db_index=True)
    key_hash = models.CharField(max_length=256)
    scopes = models.TextField(blank=True, help_text="Space-delimited scopes granted to this key.")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    allowed_origins = models.JSONField(default=list, blank=True)
    allowed_ips = models.JSONField(default=list, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "status"]), models.Index(fields=["organization", "status"]), models.Index(fields=["key_prefix"])]

    @property
    def is_active(self):
        if self.status != self.Status.ACTIVE:
            return False
        return not self.expires_at or self.expires_at > timezone.now()

    def revoke(self):
        self.status = self.Status.REVOKED
        self.revoked_at = timezone.now()
        self.save(update_fields=["status", "revoked_at", "updated_at"])

    def mark_used(self):
        self.last_used_at = timezone.now()
        self.save(update_fields=["last_used_at", "updated_at"])

    def __str__(self):
        return f"portal-api-key:{self.user_id}:{self.name}"


class PortalSupportRequest(models.Model):
    """Customer-originated support request linked to auth, billing, or organization context."""

    class Category(models.TextChoices):
        ACCOUNT = "account", _("Account")
        SECURITY = "security", _("Security")
        BILLING = "billing", _("Billing")
        ORGANIZATION = "organization", _("Organization")
        INTEGRATION = "integration", _("Integration")
        PRIVACY = "privacy", _("Privacy")
        OTHER = "other", _("Other")

    class Status(models.TextChoices):
        OPEN = "open", _("Open")
        WAITING_ON_CUSTOMER = "waiting_on_customer", _("Waiting on customer")
        WAITING_ON_SUPPORT = "waiting_on_support", _("Waiting on support")
        RESOLVED = "resolved", _("Resolved")
        CLOSED = "closed", _("Closed")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="portal_support_requests")
    organization = models.ForeignKey("accounts.Organization", on_delete=models.SET_NULL, null=True, blank=True, related_name="portal_support_requests")
    category = models.CharField(max_length=24, choices=Category.choices, default=Category.OTHER)
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.OPEN)
    subject = models.CharField(max_length=200)
    message = models.TextField()
    priority = models.CharField(max_length=16, default="normal")
    related_object_type = models.CharField(max_length=80, blank=True)
    related_object_id = models.CharField(max_length=128, blank=True)
    operator_task_id = models.UUIDField(null=True, blank=True, help_text="Optional admin_console.OperatorTask link created by support escalation.")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "status"]), models.Index(fields=["organization", "status"]), models.Index(fields=["category", "status"])]

    def mark_resolved(self):
        self.status = self.Status.RESOLVED
        self.resolved_at = timezone.now()
        self.save(update_fields=["status", "resolved_at", "updated_at"])

    def __str__(self):
        return self.subject


class PortalActivityLog(models.Model):
    """Customer-visible activity log; excludes sensitive secrets and raw payment data."""

    class Domain(models.TextChoices):
        AUTH = "auth", _("Auth")
        SECURITY = "security", _("Security")
        BILLING = "billing", _("Billing")
        ORGANIZATION = "organization", _("Organization")
        API = "api", _("API")
        PRIVACY = "privacy", _("Privacy")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="portal_activity_logs")
    organization = models.ForeignKey("accounts.Organization", on_delete=models.SET_NULL, null=True, blank=True, related_name="portal_activity_logs")
    domain = models.CharField(max_length=24, choices=Domain.choices)
    event_type = models.CharField(max_length=120)
    title = models.CharField(max_length=200)
    summary = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "domain", "created_at"]), models.Index(fields=["organization", "domain", "created_at"]), models.Index(fields=["event_type"])]

    def __str__(self):
        return f"{self.domain}:{self.event_type}:{self.user_id}"
