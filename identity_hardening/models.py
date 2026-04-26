import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class PasskeyCredential(models.Model):
    """WebAuthn/passkey credential metadata. Store no raw private keys."""

    class Status(models.TextChoices):
        ACTIVE = "active", _("Active")
        DISABLED = "disabled", _("Disabled")
        REVOKED = "revoked", _("Revoked")

    class Platform(models.TextChoices):
        WEB = "web", _("Web")
        ANDROID = "android", _("Android")
        WINDOWS = "windows", _("Windows")
        CROSS_PLATFORM = "cross_platform", _("Cross-platform")
        UNKNOWN = "unknown", _("Unknown")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="passkey_credentials")
    organization = models.ForeignKey("accounts.Organization", on_delete=models.SET_NULL, null=True, blank=True, related_name="passkey_credentials")
    label = models.CharField(max_length=160, blank=True)
    credential_id_prefix = models.CharField(max_length=32, db_index=True)
    credential_id_hash = models.CharField(max_length=256, unique=True)
    public_key_jwk = models.JSONField(default=dict, blank=True, help_text="Validated public key material in provider-neutral form.")
    sign_count = models.BigIntegerField(default=0)
    transports = models.JSONField(default=list, blank=True)
    platform = models.CharField(max_length=32, choices=Platform.choices, default=Platform.UNKNOWN)
    attestation_type = models.CharField(max_length=80, blank=True)
    aaguid = models.CharField(max_length=80, blank=True)
    backup_eligible = models.BooleanField(default=False)
    backup_state = models.BooleanField(default=False)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    last_used_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["credential_id_prefix"]),
        ]

    def mark_used(self, sign_count=None):
        self.last_used_at = timezone.now()
        if sign_count is not None:
            self.sign_count = max(int(sign_count), self.sign_count)
        self.save(update_fields=["last_used_at", "sign_count", "updated_at"])

    def revoke(self):
        self.status = self.Status.REVOKED
        self.revoked_at = timezone.now()
        self.save(update_fields=["status", "revoked_at", "updated_at"])

    def __str__(self):
        return f"passkey:{self.user_id}:{self.credential_id_prefix}"


class PasskeyChallenge(models.Model):
    """Short-lived challenge metadata for WebAuthn/passkey ceremonies."""

    class Purpose(models.TextChoices):
        REGISTRATION = "registration", _("Registration")
        AUTHENTICATION = "authentication", _("Authentication")
        STEP_UP = "step_up", _("Step-up")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name="passkey_challenges")
    organization = models.ForeignKey("accounts.Organization", on_delete=models.SET_NULL, null=True, blank=True, related_name="passkey_challenges")
    purpose = models.CharField(max_length=24, choices=Purpose.choices)
    challenge_prefix = models.CharField(max_length=32, db_index=True)
    challenge_hash = models.CharField(max_length=256, unique=True)
    rp_id = models.CharField(max_length=255)
    origin = models.CharField(max_length=255, blank=True)
    expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "purpose", "created_at"]), models.Index(fields=["challenge_prefix"])]

    @property
    def is_usable(self):
        return self.consumed_at is None and self.expires_at > timezone.now()

    def consume(self):
        self.consumed_at = timezone.now()
        self.save(update_fields=["consumed_at"])

    def __str__(self):
        return f"passkey-challenge:{self.purpose}:{self.challenge_prefix}"


class TrustedDevice(models.Model):
    """Device trust metadata for web, Android, and Windows clients."""

    class Platform(models.TextChoices):
        WEB = "web", _("Web")
        ANDROID = "android", _("Android")
        WINDOWS = "windows", _("Windows")
        API = "api", _("API")
        UNKNOWN = "unknown", _("Unknown")

    class Status(models.TextChoices):
        ACTIVE = "active", _("Active")
        UNTRUSTED = "untrusted", _("Untrusted")
        REVOKED = "revoked", _("Revoked")
        EXPIRED = "expired", _("Expired")

    class TrustLevel(models.TextChoices):
        LOW = "low", _("Low")
        STANDARD = "standard", _("Standard")
        HIGH = "high", _("High")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="trusted_devices")
    organization = models.ForeignKey("accounts.Organization", on_delete=models.SET_NULL, null=True, blank=True, related_name="trusted_devices")
    name = models.CharField(max_length=160)
    device_hash = models.CharField(max_length=256, unique=True)
    device_prefix = models.CharField(max_length=32, db_index=True)
    platform = models.CharField(max_length=24, choices=Platform.choices, default=Platform.UNKNOWN)
    trust_level = models.CharField(max_length=16, choices=TrustLevel.choices, default=TrustLevel.STANDARD)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    last_seen_ip = models.GenericIPAddressField(null=True, blank=True)
    last_seen_user_agent = models.TextField(blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-last_seen_at", "-created_at"]
        indexes = [models.Index(fields=["user", "status"]), models.Index(fields=["organization", "status"]), models.Index(fields=["device_prefix"])]

    @property
    def is_active(self):
        if self.status != self.Status.ACTIVE:
            return False
        return not self.expires_at or self.expires_at > timezone.now()

    def revoke(self):
        self.status = self.Status.REVOKED
        self.revoked_at = timezone.now()
        self.save(update_fields=["status", "revoked_at", "updated_at"])

    def __str__(self):
        return f"trusted-device:{self.user_id}:{self.name}"


class StepUpPolicy(models.Model):
    """Policy describing when sensitive actions require fresh identity proof."""

    class Trigger(models.TextChoices):
        BILLING_CHANGE = "billing_change", _("Billing change")
        PASSWORD_CHANGE = "password_change", _("Password change")
        MFA_CHANGE = "mfa_change", _("MFA change")
        API_KEY_CREATE = "api_key_create", _("API key create")
        ADMIN_ACTION = "admin_action", _("Admin action")
        SECURITY_REVIEW = "security_review", _("Security review")
        CUSTOM = "custom", _("Custom")

    class RequiredMethod(models.TextChoices):
        PASSWORD = "password", _("Password")
        TOTP = "totp", _("TOTP")
        PASSKEY = "passkey", _("Passkey")
        RECOVERY_CODE = "recovery_code", _("Recovery code")
        ANY_STRONG = "any_strong", _("Any strong method")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, null=True, blank=True, related_name="step_up_policies")
    name = models.CharField(max_length=160)
    trigger = models.CharField(max_length=32, choices=Trigger.choices)
    required_method = models.CharField(max_length=24, choices=RequiredMethod.choices, default=RequiredMethod.ANY_STRONG)
    max_age_seconds = models.PositiveIntegerField(default=900)
    min_risk_score = models.PositiveIntegerField(default=0)
    is_enforced = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["organization_id", "trigger", "name"]
        indexes = [models.Index(fields=["organization", "trigger", "is_enforced"])]

    def __str__(self):
        return f"step-up-policy:{self.trigger}:{self.name}"


class StepUpSession(models.Model):
    """Short-lived proof that a user recently satisfied a sensitive-action challenge."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="step_up_sessions")
    organization = models.ForeignKey("accounts.Organization", on_delete=models.SET_NULL, null=True, blank=True, related_name="step_up_sessions")
    method = models.CharField(max_length=24)
    trigger = models.CharField(max_length=64)
    risk_score = models.PositiveIntegerField(default=0)
    satisfied_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "trigger", "expires_at"]), models.Index(fields=["organization", "trigger"])]

    @property
    def is_valid(self):
        return self.revoked_at is None and self.expires_at > timezone.now()

    def revoke(self):
        self.revoked_at = timezone.now()
        self.save(update_fields=["revoked_at"])

    def __str__(self):
        return f"step-up:{self.user_id}:{self.trigger}:{self.method}"


class AccountRecoveryPolicy(models.Model):
    """Per-user or tenant-scoped account recovery policy."""

    class Status(models.TextChoices):
        ACTIVE = "active", _("Active")
        DISABLED = "disabled", _("Disabled")
        REVIEW_REQUIRED = "review_required", _("Review required")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name="recovery_policies")
    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, null=True, blank=True, related_name="recovery_policies")
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.ACTIVE)
    allowed_methods = models.JSONField(default=list, blank=True)
    require_operator_review = models.BooleanField(default=False)
    require_mfa_reset_delay = models.BooleanField(default=True)
    cooldown_hours = models.PositiveIntegerField(default=24)
    recovery_contact_email = models.EmailField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [models.Index(fields=["user", "status"]), models.Index(fields=["organization", "status"])]

    def __str__(self):
        return f"recovery-policy:{self.user_id or self.organization_id}"


class IdentityAssuranceEvent(models.Model):
    """Append-only ledger for passkey, trusted-device, and step-up events."""

    class Result(models.TextChoices):
        SUCCESS = "success", _("Success")
        FAILED = "failed", _("Failed")
        BLOCKED = "blocked", _("Blocked")
        REVIEW = "review", _("Review")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="identity_assurance_events")
    organization = models.ForeignKey("accounts.Organization", on_delete=models.SET_NULL, null=True, blank=True, related_name="identity_assurance_events")
    event_type = models.CharField(max_length=120)
    result = models.CharField(max_length=16, choices=Result.choices)
    method = models.CharField(max_length=32, blank=True)
    risk_score = models.PositiveIntegerField(default=0)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "event_type", "created_at"]), models.Index(fields=["organization", "event_type", "created_at"]), models.Index(fields=["result", "risk_score"])]

    def __str__(self):
        return f"identity-event:{self.event_type}:{self.result}"
