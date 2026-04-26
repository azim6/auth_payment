import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class SecurityRiskEvent(models.Model):
    """Append-only risk signal from auth, billing, OAuth, service credentials, or admin actions."""

    class Category(models.TextChoices):
        AUTH = "auth", _("Authentication")
        BILLING = "billing", _("Billing")
        OAUTH = "oauth", _("OAuth/OIDC")
        SERVICE = "service", _("Service credential")
        ADMIN = "admin", _("Admin")
        PLATFORM = "platform", _("Platform")

    class Severity(models.TextChoices):
        LOW = "low", _("Low")
        MEDIUM = "medium", _("Medium")
        HIGH = "high", _("High")
        CRITICAL = "critical", _("Critical")

    class Status(models.TextChoices):
        OPEN = "open", _("Open")
        ACKNOWLEDGED = "acknowledged", _("Acknowledged")
        RESOLVED = "resolved", _("Resolved")
        FALSE_POSITIVE = "false_positive", _("False positive")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.CharField(max_length=24, choices=Category.choices)
    severity = models.CharField(max_length=16, choices=Severity.choices, default=Severity.LOW)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.OPEN)
    signal = models.CharField(max_length=120, help_text="Machine-readable signal code, e.g. auth.impossible_travel.")
    score = models.PositiveSmallIntegerField(default=0, help_text="0-100 normalized risk score.")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="security_risk_events")
    organization = models.ForeignKey("accounts.Organization", on_delete=models.SET_NULL, null=True, blank=True, related_name="security_risk_events")
    subscription = models.ForeignKey("billing.Subscription", on_delete=models.SET_NULL, null=True, blank=True, related_name="security_risk_events")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    summary = models.CharField(max_length=255)
    metadata = models.JSONField(default=dict, blank=True)
    acknowledged_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="security_risk_events_acknowledged")
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="security_risk_events_resolved")
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["category", "severity", "status"]),
            models.Index(fields=["signal"]),
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["organization", "created_at"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.severity}:{self.signal}:{self.status}"

    def acknowledge(self, actor):
        self.status = self.Status.ACKNOWLEDGED
        self.acknowledged_by = actor
        self.acknowledged_at = timezone.now()
        self.save(update_fields=["status", "acknowledged_by", "acknowledged_at"])

    def resolve(self, actor, false_positive=False):
        self.status = self.Status.FALSE_POSITIVE if false_positive else self.Status.RESOLVED
        self.resolved_by = actor
        self.resolved_at = timezone.now()
        self.save(update_fields=["status", "resolved_by", "resolved_at"])


class AccountRestriction(models.Model):
    """Operational restriction that can limit login, API, billing, or org admin access."""

    class RestrictionType(models.TextChoices):
        LOGIN_BLOCK = "login_block", _("Login blocked")
        API_BLOCK = "api_block", _("API blocked")
        BILLING_BLOCK = "billing_block", _("Billing blocked")
        PAYMENT_REVIEW = "payment_review", _("Payment review")
        ORG_ADMIN_LOCK = "org_admin_lock", _("Organization admin locked")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="account_restrictions")
    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, null=True, blank=True, related_name="account_restrictions")
    restriction_type = models.CharField(max_length=32, choices=RestrictionType.choices)
    reason = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    starts_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(null=True, blank=True)
    lifted_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="account_restrictions_created")
    lifted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="account_restrictions_lifted")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "restriction_type", "lifted_at"]),
            models.Index(fields=["organization", "restriction_type", "lifted_at"]),
            models.Index(fields=["expires_at"]),
        ]

    @property
    def is_active(self):
        if self.lifted_at is not None:
            return False
        if self.expires_at and timezone.now() >= self.expires_at:
            return False
        return timezone.now() >= self.starts_at

    def lift(self, actor):
        if self.lifted_at is None:
            self.lifted_at = timezone.now()
            self.lifted_by = actor
            self.save(update_fields=["lifted_at", "lifted_by", "updated_at"])

    def __str__(self):
        return f"{self.user_id}:{self.restriction_type}:{'active' if self.is_active else 'inactive'}"


class SecurityIncident(models.Model):
    """Case-management record for coordinated auth/billing/security investigations."""

    class Severity(models.TextChoices):
        LOW = "low", _("Low")
        MEDIUM = "medium", _("Medium")
        HIGH = "high", _("High")
        CRITICAL = "critical", _("Critical")

    class Status(models.TextChoices):
        OPEN = "open", _("Open")
        INVESTIGATING = "investigating", _("Investigating")
        CONTAINED = "contained", _("Contained")
        RESOLVED = "resolved", _("Resolved")
        CLOSED = "closed", _("Closed")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    severity = models.CharField(max_length=16, choices=Severity.choices, default=Severity.MEDIUM)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.OPEN)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="owned_security_incidents")
    related_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="security_incidents")
    related_organization = models.ForeignKey("accounts.Organization", on_delete=models.SET_NULL, null=True, blank=True, related_name="security_incidents")
    risk_events = models.ManyToManyField(SecurityRiskEvent, blank=True, related_name="incidents")
    description = models.TextField(blank=True)
    containment_notes = models.TextField(blank=True)
    resolution_notes = models.TextField(blank=True)
    opened_at = models.DateTimeField(default=timezone.now)
    contained_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-opened_at"]
        indexes = [
            models.Index(fields=["severity", "status"]),
            models.Index(fields=["related_user", "status"]),
            models.Index(fields=["related_organization", "status"]),
        ]

    def __str__(self):
        return f"{self.severity}:{self.title}"
