import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class EnterpriseIdentityProvider(models.Model):
    """Enterprise identity provider connection for SAML/OIDC SSO.

    v27 stores provider-neutral SSO connection data and SAML metadata
    placeholders. Wire the assertion/metadata verification paths to a vetted
    SAML/OIDC library before enabling external production federation.
    """

    class Protocol(models.TextChoices):
        SAML2 = "saml2", _("SAML 2.0")
        OIDC = "oidc", _("OpenID Connect")

    class Status(models.TextChoices):
        DRAFT = "draft", _("Draft")
        TESTING = "testing", _("Testing")
        ACTIVE = "active", _("Active")
        SUSPENDED = "suspended", _("Suspended")
        DISABLED = "disabled", _("Disabled")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, related_name="enterprise_identity_providers")
    name = models.CharField(max_length=180)
    slug = models.SlugField(max_length=80)
    protocol = models.CharField(max_length=16, choices=Protocol.choices, default=Protocol.SAML2)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    entity_id = models.CharField(max_length=500, blank=True)
    sso_url = models.URLField(blank=True)
    slo_url = models.URLField(blank=True)
    x509_certificate_fingerprint = models.CharField(max_length=160, blank=True)
    x509_certificate_pem = models.TextField(blank=True, help_text="Store encrypted-at-rest in production if certificates contain sensitive metadata.")
    metadata_url = models.URLField(blank=True)
    metadata_xml = models.TextField(blank=True)
    oidc_issuer = models.URLField(blank=True)
    client_id = models.CharField(max_length=255, blank=True)
    client_secret_hash = models.CharField(max_length=256, blank=True)
    default_role = models.CharField(max_length=16, default="member")
    allowed_groups = models.JSONField(default=list, blank=True)
    attribute_mapping = models.JSONField(default=dict, blank=True)
    require_signed_assertions = models.BooleanField(default=True)
    require_encrypted_assertions = models.BooleanField(default=False)
    allow_idp_initiated_login = models.BooleanField(default=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="enterprise_idps_created")
    last_tested_at = models.DateTimeField(null=True, blank=True)
    activated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("organization", "slug")]
        ordering = ["organization__slug", "name"]
        indexes = [
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["protocol", "status"]),
            models.Index(fields=["entity_id"]),
        ]

    def __str__(self):
        return f"{self.organization.slug}:{self.slug}:{self.protocol}"

    def mark_tested(self):
        self.last_tested_at = timezone.now()
        if self.status == self.Status.DRAFT:
            self.status = self.Status.TESTING
        self.save(update_fields=["last_tested_at", "status", "updated_at"])

    def activate(self):
        now = timezone.now()
        self.status = self.Status.ACTIVE
        self.activated_at = now
        self.save(update_fields=["status", "activated_at", "updated_at"])

    def disable(self):
        self.status = self.Status.DISABLED
        self.save(update_fields=["status", "updated_at"])


class VerifiedDomain(models.Model):
    """Organization-owned email/domain proof for enterprise SSO routing."""

    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        VERIFIED = "verified", _("Verified")
        FAILED = "failed", _("Failed")
        REVOKED = "revoked", _("Revoked")

    class Method(models.TextChoices):
        DNS_TXT = "dns_txt", _("DNS TXT")
        HTTP_FILE = "http_file", _("HTTP file")
        MANUAL = "manual", _("Manual review")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, related_name="verified_domains")
    domain = models.CharField(max_length=255)
    method = models.CharField(max_length=24, choices=Method.choices, default=Method.DNS_TXT)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    verification_token_prefix = models.CharField(max_length=32, blank=True, db_index=True)
    verification_token_hash = models.CharField(max_length=256, blank=True)
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="enterprise_domains_verified")
    verified_at = models.DateTimeField(null=True, blank=True)
    last_checked_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("organization", "domain")]
        ordering = ["domain"]
        indexes = [
            models.Index(fields=["domain", "status"]),
            models.Index(fields=["organization", "status"]),
        ]

    def __str__(self):
        return f"{self.domain}:{self.status}"

    def mark_verified(self, user=None):
        self.status = self.Status.VERIFIED
        self.verified_by = user or self.verified_by
        self.verified_at = timezone.now()
        self.last_checked_at = self.verified_at
        self.failure_reason = ""
        self.save(update_fields=["status", "verified_by", "verified_at", "last_checked_at", "failure_reason", "updated_at"])


class SsoPolicy(models.Model):
    """Tenant-level SSO enforcement and JIT provisioning policy."""

    class Enforcement(models.TextChoices):
        OPTIONAL = "optional", _("Optional")
        REQUIRED_FOR_DOMAIN = "required_for_domain", _("Required for verified domains")
        REQUIRED_FOR_ALL = "required_for_all", _("Required for all members")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.OneToOneField("accounts.Organization", on_delete=models.CASCADE, related_name="sso_policy")
    enforcement = models.CharField(max_length=32, choices=Enforcement.choices, default=Enforcement.OPTIONAL)
    default_identity_provider = models.ForeignKey(EnterpriseIdentityProvider, on_delete=models.SET_NULL, null=True, blank=True, related_name="default_for_policies")
    allow_password_fallback_for_owners = models.BooleanField(default=True)
    allow_jit_provisioning = models.BooleanField(default=False)
    require_verified_domain_for_jit = models.BooleanField(default=True)
    require_mfa_after_sso = models.BooleanField(default=False)
    allowed_email_domains = models.JSONField(default=list, blank=True)
    blocked_email_domains = models.JSONField(default=list, blank=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="sso_policies_updated")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["organization__slug"]

    def __str__(self):
        return f"sso-policy:{self.organization.slug}:{self.enforcement}"


class JitProvisioningRule(models.Model):
    """Rules for mapping SSO claims/groups to organization roles."""

    class Status(models.TextChoices):
        ACTIVE = "active", _("Active")
        DISABLED = "disabled", _("Disabled")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, related_name="jit_rules")
    identity_provider = models.ForeignKey(EnterpriseIdentityProvider, on_delete=models.CASCADE, related_name="jit_rules")
    name = models.CharField(max_length=180)
    priority = models.PositiveIntegerField(default=100)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    claim = models.CharField(max_length=120, default="groups")
    operator = models.CharField(max_length=24, default="contains")
    value = models.CharField(max_length=255)
    assigned_role = models.CharField(max_length=16, default="member")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["organization__slug", "priority", "name"]
        indexes = [
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["identity_provider", "status"]),
        ]

    def __str__(self):
        return f"jit:{self.organization.slug}:{self.name}"


class SsoLoginEvent(models.Model):
    """Append-only SSO login, test, and provisioning event ledger."""

    class Result(models.TextChoices):
        SUCCESS = "success", _("Success")
        FAILURE = "failure", _("Failure")
        BLOCKED = "blocked", _("Blocked")
        TEST = "test", _("Test")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey("accounts.Organization", on_delete=models.SET_NULL, null=True, blank=True, related_name="sso_login_events")
    identity_provider = models.ForeignKey(EnterpriseIdentityProvider, on_delete=models.SET_NULL, null=True, blank=True, related_name="login_events")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="sso_login_events")
    email = models.EmailField(blank=True)
    subject = models.CharField(max_length=255, blank=True)
    result = models.CharField(max_length=16, choices=Result.choices)
    reason = models.CharField(max_length=255, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    attributes = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "created_at"]),
            models.Index(fields=["identity_provider", "created_at"]),
            models.Index(fields=["email", "created_at"]),
            models.Index(fields=["result", "created_at"]),
        ]

    def __str__(self):
        return f"sso-event:{self.email or self.subject}:{self.result}"
