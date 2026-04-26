import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class DeviceFingerprint(models.Model):
    """Hashed device fingerprint observed across auth, checkout, and API sessions."""

    class TrustLevel(models.TextChoices):
        UNKNOWN = "unknown", _("Unknown")
        TRUSTED = "trusted", _("Trusted")
        WATCH = "watch", _("Watch")
        BLOCKED = "blocked", _("Blocked")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fingerprint_hash = models.CharField(max_length=128, unique=True)
    trust_level = models.CharField(max_length=16, choices=TrustLevel.choices, default=TrustLevel.UNKNOWN)
    first_seen_at = models.DateTimeField(default=timezone.now)
    last_seen_at = models.DateTimeField(default=timezone.now)
    last_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="last_seen_device_fingerprints")
    last_organization = models.ForeignKey("accounts.Organization", on_delete=models.SET_NULL, null=True, blank=True, related_name="last_seen_device_fingerprints")
    user_count = models.PositiveIntegerField(default=0)
    ip_count = models.PositiveIntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_device_fingerprints")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-last_seen_at"]
        indexes = [
            models.Index(fields=["fingerprint_hash"]),
            models.Index(fields=["trust_level", "last_seen_at"]),
            models.Index(fields=["last_user", "last_seen_at"]),
        ]

    def __str__(self):
        return f"{self.fingerprint_hash[:12]}:{self.trust_level}"


class IPReputation(models.Model):
    """Internal reputation record for IPs and CIDR/network-derived signals."""

    class Reputation(models.TextChoices):
        GOOD = "good", _("Good")
        UNKNOWN = "unknown", _("Unknown")
        SUSPICIOUS = "suspicious", _("Suspicious")
        BAD = "bad", _("Bad")
        BLOCKED = "blocked", _("Blocked")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ip_address = models.GenericIPAddressField(unique=True)
    reputation = models.CharField(max_length=16, choices=Reputation.choices, default=Reputation.UNKNOWN)
    risk_score = models.PositiveSmallIntegerField(default=0)
    country_code = models.CharField(max_length=2, blank=True)
    asn = models.CharField(max_length=32, blank=True)
    source = models.CharField(max_length=80, default="internal")
    first_seen_at = models.DateTimeField(default=timezone.now)
    last_seen_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-risk_score", "-last_seen_at"]
        indexes = [
            models.Index(fields=["ip_address"]),
            models.Index(fields=["reputation", "risk_score"]),
            models.Index(fields=["expires_at"]),
        ]

    @property
    def is_active(self):
        return self.expires_at is None or timezone.now() < self.expires_at

    def __str__(self):
        return f"{self.ip_address}:{self.reputation}:{self.risk_score}"


class AbuseSignal(models.Model):
    """Append-only normalized signal emitted by auth, billing, notifications, platform, or an app."""

    class Category(models.TextChoices):
        AUTH = "auth", _("Authentication")
        BILLING = "billing", _("Billing")
        PAYMENT = "payment", _("Payment")
        API = "api", _("API")
        CONTENT = "content", _("Content")
        NOTIFICATION = "notification", _("Notification")
        PLATFORM = "platform", _("Platform")

    class Severity(models.TextChoices):
        INFO = "info", _("Info")
        LOW = "low", _("Low")
        MEDIUM = "medium", _("Medium")
        HIGH = "high", _("High")
        CRITICAL = "critical", _("Critical")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.CharField(max_length=24, choices=Category.choices)
    signal = models.CharField(max_length=120)
    severity = models.CharField(max_length=16, choices=Severity.choices, default=Severity.LOW)
    score = models.PositiveSmallIntegerField(default=0)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="abuse_signals")
    organization = models.ForeignKey("accounts.Organization", on_delete=models.SET_NULL, null=True, blank=True, related_name="abuse_signals")
    subscription = models.ForeignKey("billing.Subscription", on_delete=models.SET_NULL, null=True, blank=True, related_name="abuse_signals")
    device = models.ForeignKey(DeviceFingerprint, on_delete=models.SET_NULL, null=True, blank=True, related_name="abuse_signals")
    ip_reputation = models.ForeignKey(IPReputation, on_delete=models.SET_NULL, null=True, blank=True, related_name="abuse_signals")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    summary = models.CharField(max_length=255)
    metadata = models.JSONField(default=dict, blank=True)
    event_idempotency_key = models.CharField(max_length=160, blank=True, null=True, unique=True)
    observed_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-observed_at"]
        indexes = [
            models.Index(fields=["category", "signal"]),
            models.Index(fields=["severity", "score"]),
            models.Index(fields=["user", "observed_at"]),
            models.Index(fields=["organization", "observed_at"]),
            models.Index(fields=["ip_address", "observed_at"]),
        ]

    def __str__(self):
        return f"{self.category}:{self.signal}:{self.score}"


class VelocityRule(models.Model):
    """Configurable rule for detecting spikes such as login failures, registrations, or checkout attempts."""

    class Action(models.TextChoices):
        MONITOR = "monitor", _("Monitor")
        REVIEW = "review", _("Review")
        CHALLENGE = "challenge", _("Challenge")
        RESTRICT = "restrict", _("Restrict")
        BLOCK = "block", _("Block")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=160)
    event_name = models.CharField(max_length=120, help_text="Machine event name, e.g. auth.login_failed or billing.checkout_created.")
    scope = models.CharField(max_length=32, default="user", help_text="user, organization, ip, device, or global.")
    threshold = models.PositiveIntegerField()
    window_seconds = models.PositiveIntegerField(default=300)
    action = models.CharField(max_length=16, choices=Action.choices, default=Action.REVIEW)
    risk_score = models.PositiveSmallIntegerField(default=50)
    enabled = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["event_name", "scope", "threshold"]
        indexes = [
            models.Index(fields=["event_name", "scope", "enabled"]),
            models.Index(fields=["enabled"]),
        ]

    def __str__(self):
        return f"{self.event_name}:{self.scope}:{self.threshold}/{self.window_seconds}s"


class VelocityEvent(models.Model):
    """Append-only event used for velocity/rate anomaly calculations."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_name = models.CharField(max_length=120)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="velocity_events")
    organization = models.ForeignKey("accounts.Organization", on_delete=models.SET_NULL, null=True, blank=True, related_name="velocity_events")
    device = models.ForeignKey(DeviceFingerprint, on_delete=models.SET_NULL, null=True, blank=True, related_name="velocity_events")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    occurred_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-occurred_at"]
        indexes = [
            models.Index(fields=["event_name", "occurred_at"]),
            models.Index(fields=["user", "event_name", "occurred_at"]),
            models.Index(fields=["organization", "event_name", "occurred_at"]),
            models.Index(fields=["ip_address", "event_name", "occurred_at"]),
        ]

    def __str__(self):
        return f"{self.event_name}:{self.occurred_at.isoformat()}"


class AbuseCase(models.Model):
    """Investigation case for fraud, abuse, account takeover, spam, or payment risk."""

    class CaseType(models.TextChoices):
        ACCOUNT_TAKEOVER = "account_takeover", _("Account takeover")
        PAYMENT_FRAUD = "payment_fraud", _("Payment fraud")
        SPAM = "spam", _("Spam")
        API_ABUSE = "api_abuse", _("API abuse")
        POLICY = "policy", _("Policy abuse")
        OTHER = "other", _("Other")

    class Status(models.TextChoices):
        OPEN = "open", _("Open")
        REVIEWING = "reviewing", _("Reviewing")
        MITIGATED = "mitigated", _("Mitigated")
        RESOLVED = "resolved", _("Resolved")
        FALSE_POSITIVE = "false_positive", _("False positive")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case_type = models.CharField(max_length=32, choices=CaseType.choices)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.OPEN)
    severity = models.CharField(max_length=16, choices=AbuseSignal.Severity.choices, default=AbuseSignal.Severity.MEDIUM)
    title = models.CharField(max_length=200)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="abuse_cases")
    organization = models.ForeignKey("accounts.Organization", on_delete=models.SET_NULL, null=True, blank=True, related_name="abuse_cases")
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="owned_abuse_cases")
    signals = models.ManyToManyField(AbuseSignal, blank=True, related_name="abuse_cases")
    summary = models.TextField(blank=True)
    resolution_notes = models.TextField(blank=True)
    opened_at = models.DateTimeField(default=timezone.now)
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-opened_at"]
        indexes = [
            models.Index(fields=["case_type", "status"]),
            models.Index(fields=["severity", "status"]),
            models.Index(fields=["user", "status"]),
            models.Index(fields=["organization", "status"]),
        ]

    def __str__(self):
        return f"{self.case_type}:{self.title}:{self.status}"


class PaymentRiskReview(models.Model):
    """Review queue item connected to invoices, transactions, checkout sessions, or subscriptions."""

    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        APPROVED = "approved", _("Approved")
        REJECTED = "rejected", _("Rejected")
        ESCALATED = "escalated", _("Escalated")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, related_name="payment_risk_reviews")
    customer = models.ForeignKey("billing.BillingCustomer", on_delete=models.SET_NULL, null=True, blank=True, related_name="payment_risk_reviews")
    subscription = models.ForeignKey("billing.Subscription", on_delete=models.SET_NULL, null=True, blank=True, related_name="payment_risk_reviews")
    invoice = models.ForeignKey("billing.Invoice", on_delete=models.SET_NULL, null=True, blank=True, related_name="payment_risk_reviews")
    transaction = models.ForeignKey("billing.PaymentTransaction", on_delete=models.SET_NULL, null=True, blank=True, related_name="payment_risk_reviews")
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.PENDING)
    risk_score = models.PositiveSmallIntegerField(default=0)
    reason = models.TextField()
    decision_notes = models.TextField(blank=True)
    signals = models.ManyToManyField(AbuseSignal, blank=True, related_name="payment_risk_reviews")
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_payment_risks")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["risk_score", "status"]),
        ]

    def apply_decision(self, actor, status_value, notes=""):
        self.status = status_value
        self.reviewed_by = actor
        self.reviewed_at = timezone.now()
        self.decision_notes = notes
        self.save(update_fields=["status", "reviewed_by", "reviewed_at", "decision_notes", "updated_at"])

    def __str__(self):
        return f"{self.organization_id}:{self.risk_score}:{self.status}"
