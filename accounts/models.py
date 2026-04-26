import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .managers import UserManager


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(_("email address"), unique=True)
    display_name = models.CharField(max_length=150, blank=True)
    avatar_url = models.URLField(blank=True)
    bio = models.TextField(blank=True)
    email_verified = models.BooleanField(default=False)
    terms_accepted_at = models.DateTimeField(null=True, blank=True)
    privacy_policy_accepted_at = models.DateTimeField(null=True, blank=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    objects = UserManager()

    class Meta:
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["username"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return self.email

    @property
    def public_name(self):
        return self.display_name or self.username


class AccountToken(models.Model):
    class Purpose(models.TextChoices):
        EMAIL_VERIFICATION = "email_verification", _("Email verification")
        PASSWORD_RESET = "password_reset", _("Password reset")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="account_tokens")
    purpose = models.CharField(max_length=32, choices=Purpose.choices)
    token_hash = models.CharField(max_length=128, unique=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "purpose"]),
            models.Index(fields=["token_hash"]),
            models.Index(fields=["expires_at"]),
        ]

    def __str__(self):
        return f"{self.purpose}:{self.user_id}"

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at

    @property
    def is_used(self):
        return self.used_at is not None

    def mark_used(self):
        self.used_at = timezone.now()
        self.save(update_fields=["used_at"])


class MfaDevice(models.Model):
    class Type(models.TextChoices):
        TOTP = "totp", _("Authenticator app TOTP")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="mfa_device")
    type = models.CharField(max_length=16, choices=Type.choices, default=Type.TOTP)
    name = models.CharField(max_length=120, default="Authenticator app")
    secret = models.TextField(help_text="Signed TOTP secret. Do not expose through APIs.")
    confirmed_at = models.DateTimeField(null=True, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["user", "confirmed_at"])]

    def __str__(self):
        return f"{self.type}:{self.user_id}"

    @property
    def is_confirmed(self):
        return self.confirmed_at is not None

    def mark_confirmed(self):
        now = timezone.now()
        self.confirmed_at = self.confirmed_at or now
        self.last_used_at = now
        self.save(update_fields=["confirmed_at", "last_used_at", "updated_at"])

    def mark_used(self):
        self.last_used_at = timezone.now()
        self.save(update_fields=["last_used_at", "updated_at"])


class RecoveryCode(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="recovery_codes")
    code_hash = models.CharField(max_length=256)
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["user", "used_at"])]

    def __str__(self):
        return f"recovery-code:{self.user_id}"

    @property
    def is_used(self):
        return self.used_at is not None

    def mark_used(self):
        self.used_at = timezone.now()
        self.save(update_fields=["used_at"])

class OAuthClient(models.Model):
    """Registered relying-party application for OIDC/OAuth-style login.

    v4 intentionally implements the production data model and authorization-code
    exchange foundation. Keep consent, dynamic client registration, and external
    federation behind explicit future work.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="owned_oauth_clients")
    name = models.CharField(max_length=150)
    client_id = models.CharField(max_length=80, unique=True)
    client_secret_hash = models.CharField(max_length=256, blank=True)
    is_confidential = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    redirect_uris = models.TextField(help_text="One redirect URI per line. Exact match required.")
    allowed_scopes = models.CharField(max_length=255, default="openid profile email")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["client_id"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.client_id})"

    @property
    def redirect_uri_list(self):
        return [uri.strip() for uri in self.redirect_uris.splitlines() if uri.strip()]

    @property
    def scope_set(self):
        return {scope for scope in self.allowed_scopes.split() if scope}


class AuthorizationCode(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(OAuthClient, on_delete=models.CASCADE, related_name="authorization_codes")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="authorization_codes")
    code_hash = models.CharField(max_length=128, unique=True)
    redirect_uri = models.CharField(max_length=500)
    scope = models.CharField(max_length=255, default="openid profile email")
    state = models.CharField(max_length=255, blank=True)
    nonce = models.CharField(max_length=255, blank=True)
    code_challenge = models.CharField(max_length=255, blank=True)
    code_challenge_method = models.CharField(max_length=16, blank=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["client", "user"]),
            models.Index(fields=["code_hash"]),
            models.Index(fields=["expires_at"]),
        ]

    def __str__(self):
        return f"authorization-code:{self.client_id}:{self.user_id}"

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at

    @property
    def is_used(self):
        return self.used_at is not None

    def mark_used(self):
        self.used_at = timezone.now()
        self.save(update_fields=["used_at"])

class AuditLog(models.Model):
    """Append-only security/audit event for account, OAuth, and service actions."""

    class Category(models.TextChoices):
        AUTH = "auth", _("Authentication")
        ACCOUNT = "account", _("Account")
        MFA = "mfa", _("MFA")
        OAUTH = "oauth", _("OAuth/OIDC")
        SERVICE = "service", _("Service credential")
        ADMIN = "admin", _("Admin")

    class Outcome(models.TextChoices):
        SUCCESS = "success", _("Success")
        FAILURE = "failure", _("Failure")
        DENIED = "denied", _("Denied")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_events")
    category = models.CharField(max_length=24, choices=Category.choices)
    action = models.CharField(max_length=80)
    outcome = models.CharField(max_length=16, choices=Outcome.choices, default=Outcome.SUCCESS)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    request_id = models.CharField(max_length=100, blank=True)
    client_id = models.CharField(max_length=120, blank=True)
    subject_user_id = models.UUIDField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["category", "action"]),
            models.Index(fields=["outcome"]),
            models.Index(fields=["actor", "created_at"]),
            models.Index(fields=["client_id", "created_at"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.category}:{self.action}:{self.outcome}"


class ServiceCredential(models.Model):
    """Hashed API credential for trusted internal service-to-service calls."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="service_credentials")
    name = models.CharField(max_length=150)
    key_prefix = models.CharField(max_length=16, unique=True)
    key_hash = models.CharField(max_length=256)
    scopes = models.CharField(max_length=255, default="users:read tokens:introspect")
    is_active = models.BooleanField(default=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["key_prefix"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["expires_at"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.key_prefix})"

    @property
    def scope_set(self):
        return {scope for scope in self.scopes.split() if scope}

    @property
    def is_expired(self):
        return self.expires_at is not None and timezone.now() >= self.expires_at

    def mark_used(self):
        self.last_used_at = timezone.now()
        self.save(update_fields=["last_used_at", "updated_at"])


class OAuthTokenActivity(models.Model):
    """Queryable token lifecycle record for revocation, introspection, and admin audit."""

    class TokenType(models.TextChoices):
        ACCESS = "access", _("Access token")
        REFRESH = "refresh", _("Refresh token")
        ID = "id", _("ID token")
        SERVICE = "service", _("Service token")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    jti = models.CharField(max_length=255, unique=True)
    token_type = models.CharField(max_length=16, choices=TokenType.choices)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="oauth_token_activity")
    client = models.ForeignKey(OAuthClient, on_delete=models.SET_NULL, null=True, blank=True, related_name="token_activity")
    service_credential = models.ForeignKey(ServiceCredential, on_delete=models.SET_NULL, null=True, blank=True, related_name="token_activity")
    scope = models.CharField(max_length=255, blank=True)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["jti"]),
            models.Index(fields=["token_type"]),
            models.Index(fields=["client", "created_at"]),
            models.Index(fields=["service_credential", "created_at"]),
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["expires_at"]),
            models.Index(fields=["revoked_at"]),
        ]

    def __str__(self):
        return f"{self.token_type}:{self.jti}"

    @property
    def is_active(self):
        return self.revoked_at is None and timezone.now() < self.expires_at

    def revoke(self):
        if self.revoked_at is None:
            self.revoked_at = timezone.now()
            self.save(update_fields=["revoked_at"])

    def mark_seen(self):
        self.last_seen_at = timezone.now()
        self.save(update_fields=["last_seen_at"])


class AuthSessionDevice(models.Model):
    """Server-side inventory of browser/API sessions by device fingerprint."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="auth_session_devices")
    session_key_hash = models.CharField(max_length=128, db_index=True)
    label = models.CharField(max_length=120, blank=True)
    user_agent = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    last_seen_at = models.DateTimeField(default=timezone.now)
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-last_seen_at"]
        indexes = [
            models.Index(fields=["user", "last_seen_at"]),
            models.Index(fields=["session_key_hash"]),
            models.Index(fields=["revoked_at"]),
        ]

    @property
    def is_active(self):
        return self.revoked_at is None

    def revoke(self):
        if self.revoked_at is None:
            self.revoked_at = timezone.now()
            self.save(update_fields=["revoked_at", "updated_at"])


class RefreshTokenFamily(models.Model):
    """Refresh-token family inventory for mobile/desktop logout-all operations."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="refresh_token_families")
    jti = models.CharField(max_length=255, unique=True)
    parent_jti = models.CharField(max_length=255, blank=True)
    client_id = models.CharField(max_length=120, blank=True)
    user_agent = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["jti"]),
            models.Index(fields=["client_id", "created_at"]),
            models.Index(fields=["expires_at"]),
            models.Index(fields=["revoked_at"]),
        ]

    @property
    def is_active(self):
        return self.revoked_at is None and timezone.now() < self.expires_at

    def revoke(self):
        if self.revoked_at is None:
            self.revoked_at = timezone.now()
            self.save(update_fields=["revoked_at"])

class PrivacyPreference(models.Model):
    """User-managed privacy and communication preferences.

    Keep this separate from authentication state so product teams can consume
    preferences without being granted direct access to passwords, sessions, or
    token tables.
    """

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="privacy_preferences")
    analytics_consent = models.BooleanField(default=False)
    marketing_email_consent = models.BooleanField(default=False)
    product_email_consent = models.BooleanField(default=True)
    profile_discoverable = models.BooleanField(default=True)
    data_processing_region = models.CharField(max_length=32, default="default")
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["user"]), models.Index(fields=["updated_at"])]

    def __str__(self):
        return f"privacy-preferences:{self.user_id}"


class UserConsent(models.Model):
    """Append-only record of legal/product consent events."""

    class ConsentType(models.TextChoices):
        TERMS = "terms", _("Terms of service")
        PRIVACY = "privacy", _("Privacy policy")
        MARKETING = "marketing", _("Marketing communications")
        ANALYTICS = "analytics", _("Analytics")

    class Source(models.TextChoices):
        WEB = "web", _("Web")
        ANDROID = "android", _("Android")
        WINDOWS = "windows", _("Windows")
        API = "api", _("API")
        ADMIN = "admin", _("Admin")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="consents")
    consent_type = models.CharField(max_length=32, choices=ConsentType.choices)
    version = models.CharField(max_length=64)
    granted = models.BooleanField(default=True)
    source = models.CharField(max_length=32, choices=Source.choices, default=Source.API)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "consent_type", "created_at"]),
            models.Index(fields=["consent_type", "version"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.consent_type}:{self.version}:{self.user_id}"


class DataExportRequest(models.Model):
    """Tracks user data export requests for privacy/compliance workflows."""

    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        PROCESSING = "processing", _("Processing")
        READY = "ready", _("Ready")
        FAILED = "failed", _("Failed")
        EXPIRED = "expired", _("Expired")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="data_export_requests")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    format = models.CharField(max_length=16, default="json")
    download_url = models.URLField(blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    error = models.TextField(blank=True)
    requested_ip = models.GenericIPAddressField(null=True, blank=True)
    requested_user_agent = models.TextField(blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["expires_at"]),
        ]

    def __str__(self):
        return f"data-export:{self.user_id}:{self.status}"

    @property
    def is_ready(self):
        return self.status == self.Status.READY and (self.expires_at is None or timezone.now() < self.expires_at)


class AccountDeletionRequest(models.Model):
    """Soft-delete/deactivation request with grace period.

    v7 does not hard-delete rows automatically. It records the request, disables
    login at confirmation time, and gives operators a safe hook for irreversible
    deletion/anonymization jobs after the grace period.
    """

    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        CONFIRMED = "confirmed", _("Confirmed")
        CANCELLED = "cancelled", _("Cancelled")
        COMPLETED = "completed", _("Completed")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="deletion_requests")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    reason = models.TextField(blank=True)
    requested_ip = models.GenericIPAddressField(null=True, blank=True)
    requested_user_agent = models.TextField(blank=True)
    confirm_before = models.DateTimeField()
    scheduled_for = models.DateTimeField()
    confirmed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["status", "scheduled_for"]),
            models.Index(fields=["confirm_before"]),
        ]

    def __str__(self):
        return f"account-deletion:{self.user_id}:{self.status}"

    @property
    def is_confirmable(self):
        return self.status == self.Status.PENDING and timezone.now() < self.confirm_before



class Organization(models.Model):
    """Tenant/workspace container for enterprise and multi-project deployments."""

    class Plan(models.TextChoices):
        FREE = "free", _("Free")
        TEAM = "team", _("Team")
        BUSINESS = "business", _("Business")
        ENTERPRISE = "enterprise", _("Enterprise")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=180)
    slug = models.SlugField(max_length=80, unique=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="owned_organizations")
    plan = models.CharField(max_length=24, choices=Plan.choices, default=Plan.FREE)
    is_active = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["owner", "created_at"]),
            models.Index(fields=["is_active", "plan"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.slug})"


class OrganizationMembership(models.Model):
    """User role inside an organization tenant."""

    class Role(models.TextChoices):
        OWNER = "owner", _("Owner")
        ADMIN = "admin", _("Admin")
        MEMBER = "member", _("Member")
        VIEWER = "viewer", _("Viewer")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="organization_memberships")
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.MEMBER)
    is_active = models.BooleanField(default=True)
    invited_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="organization_memberships_invited")
    joined_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("organization", "user")]
        ordering = ["organization", "role", "user__email"]
        indexes = [
            models.Index(fields=["organization", "role"]),
            models.Index(fields=["organization", "is_active"]),
            models.Index(fields=["user", "is_active"]),
        ]

    def __str__(self):
        return f"{self.organization.slug}:{self.user_id}:{self.role}"

    @property
    def can_manage_members(self):
        return self.is_active and self.role in {self.Role.OWNER, self.Role.ADMIN}

    @property
    def can_manage_billing_or_delete(self):
        return self.is_active and self.role == self.Role.OWNER


class OrganizationInvitation(models.Model):
    """One-time tenant invitation token for email-based onboarding."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="invitations")
    email = models.EmailField()
    role = models.CharField(max_length=16, choices=OrganizationMembership.Role.choices, default=OrganizationMembership.Role.MEMBER)
    token_hash = models.CharField(max_length=256, unique=True)
    invited_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="organization_invitations_sent")
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "email"]),
            models.Index(fields=["token_hash"]),
            models.Index(fields=["expires_at"]),
            models.Index(fields=["accepted_at", "revoked_at"]),
        ]

    def __str__(self):
        return f"invite:{self.organization.slug}:{self.email}"

    @property
    def is_active(self):
        return self.accepted_at is None and self.revoked_at is None and timezone.now() < self.expires_at

    def mark_accepted(self):
        self.accepted_at = timezone.now()
        self.save(update_fields=["accepted_at"])

    def revoke(self):
        if self.revoked_at is None:
            self.revoked_at = timezone.now()
            self.save(update_fields=["revoked_at"])


class TenantServiceCredential(models.Model):
    """Organization-scoped machine credential for tenant-specific integrations."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="service_credentials")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="tenant_service_credentials_created")
    name = models.CharField(max_length=150)
    key_prefix = models.CharField(max_length=16, unique=True)
    key_hash = models.CharField(max_length=256)
    scopes = models.CharField(max_length=255, default="org:read members:read")
    is_active = models.BooleanField(default=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["organization", "name"]
        indexes = [
            models.Index(fields=["organization", "is_active"]),
            models.Index(fields=["key_prefix"]),
            models.Index(fields=["expires_at"]),
        ]

    def __str__(self):
        return f"{self.organization.slug}:{self.name} ({self.key_prefix})"

    @property
    def scope_set(self):
        return {scope for scope in self.scopes.split() if scope}

    @property
    def is_expired(self):
        return self.expires_at is not None and timezone.now() >= self.expires_at

    def mark_used(self):
        self.last_used_at = timezone.now()
        self.save(update_fields=["last_used_at", "updated_at"])

class PermissionPolicy(models.Model):
    """Named tenant permission that can be granted/denied per organization role.

    v9 keeps RBAC explicit and auditable. Baseline role permissions live in
    accounts.authorization, while this model lets tenants add or override
    permissions without changing code.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="permission_policies")
    code = models.CharField(max_length=120)
    name = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="permission_policies_created")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("organization", "code")]
        ordering = ["organization", "code"]
        indexes = [
            models.Index(fields=["organization", "is_active"]),
            models.Index(fields=["code"]),
            models.Index(fields=["expires_at"]),
        ]

    def __str__(self):
        return f"{self.organization.slug}:{self.code}"

    @property
    def is_expired(self):
        return self.expires_at is not None and timezone.now() >= self.expires_at


class RolePermissionGrant(models.Model):
    """Allow/deny grant that maps a tenant role to a permission policy."""

    class Effect(models.TextChoices):
        ALLOW = "allow", _("Allow")
        DENY = "deny", _("Deny")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="role_permission_grants")
    role = models.CharField(max_length=16, choices=OrganizationMembership.Role.choices)
    policy = models.ForeignKey(PermissionPolicy, on_delete=models.CASCADE, related_name="role_grants")
    effect = models.CharField(max_length=8, choices=Effect.choices, default=Effect.ALLOW)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="role_permission_grants_created")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("organization", "role", "policy")]
        ordering = ["organization", "role", "policy__code"]
        indexes = [
            models.Index(fields=["organization", "role"]),
            models.Index(fields=["effect"]),
        ]

    def __str__(self):
        return f"{self.organization.slug}:{self.role}:{self.policy.code}:{self.effect}"

