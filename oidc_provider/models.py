import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from accounts.models import OAuthClient


class OidcSigningKey(models.Model):
    """Metadata for signing keys exposed through JWKS.

    Private key material should be stored in a secret manager/HSM/KMS in real
    production environments. This model tracks lifecycle, public JWK metadata,
    rotation windows, and revocation status.
    """

    class Algorithm(models.TextChoices):
        RS256 = "RS256", _("RS256")
        ES256 = "ES256", _("ES256")
        EDDSA = "EdDSA", _("EdDSA")

    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        ACTIVE = "active", _("Active")
        RETIRING = "retiring", _("Retiring")
        RETIRED = "retired", _("Retired")
        REVOKED = "revoked", _("Revoked")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    kid = models.CharField(max_length=120, unique=True)
    algorithm = models.CharField(max_length=16, choices=Algorithm.choices, default=Algorithm.RS256)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    public_jwk = models.JSONField(default=dict, blank=True)
    private_key_reference = models.CharField(max_length=300, blank=True)
    not_before = models.DateTimeField(default=timezone.now)
    not_after = models.DateTimeField(null=True, blank=True)
    activated_at = models.DateTimeField(null=True, blank=True)
    retiring_at = models.DateTimeField(null=True, blank=True)
    retired_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="created_oidc_keys")
    rotation_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["kid"]), models.Index(fields=["status"]), models.Index(fields=["not_before", "not_after"])]

    def __str__(self):
        return f"{self.kid}:{self.status}"

    @property
    def is_publishable(self):
        return self.status in {self.Status.ACTIVE, self.Status.RETIRING}

    def activate(self):
        self.status = self.Status.ACTIVE
        self.activated_at = timezone.now()
        self.save(update_fields=["status", "activated_at", "updated_at"])

    def mark_retiring(self):
        self.status = self.Status.RETIRING
        self.retiring_at = timezone.now()
        self.save(update_fields=["status", "retiring_at", "updated_at"])

    def retire(self):
        self.status = self.Status.RETIRED
        self.retired_at = timezone.now()
        self.save(update_fields=["status", "retired_at", "updated_at"])

    def revoke(self):
        self.status = self.Status.REVOKED
        self.revoked_at = timezone.now()
        self.save(update_fields=["status", "revoked_at", "updated_at"])


class OAuthScopeDefinition(models.Model):
    class Sensitivity(models.TextChoices):
        LOW = "low", _("Low")
        MEDIUM = "medium", _("Medium")
        HIGH = "high", _("High")
        RESTRICTED = "restricted", _("Restricted")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=80, unique=True)
    display_name = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    sensitivity = models.CharField(max_length=16, choices=Sensitivity.choices, default=Sensitivity.LOW)
    requires_consent = models.BooleanField(default=True)
    staff_approval_required = models.BooleanField(default=False)
    default_for_first_party = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [models.Index(fields=["name"]), models.Index(fields=["is_active", "sensitivity"])]

    def __str__(self):
        return self.name


class OAuthClaimMapping(models.Model):
    class TokenType(models.TextChoices):
        ID_TOKEN = "id_token", _("ID token")
        USERINFO = "userinfo", _("UserInfo")
        ACCESS_TOKEN = "access_token", _("Access token")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scope = models.ForeignKey(OAuthScopeDefinition, on_delete=models.CASCADE, related_name="claim_mappings")
    claim_name = models.CharField(max_length=120)
    source_path = models.CharField(max_length=160, help_text="Dotted source path, for example user.email or org.slug.")
    token_type = models.CharField(max_length=24, choices=TokenType.choices, default=TokenType.ID_TOKEN)
    include_when_empty = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("scope", "claim_name", "token_type")]
        ordering = ["scope__name", "token_type", "claim_name"]
        indexes = [models.Index(fields=["claim_name"]), models.Index(fields=["token_type", "is_active"])]

    def __str__(self):
        return f"{self.scope.name}:{self.claim_name}"


class OAuthClientTrustProfile(models.Model):
    class TrustLevel(models.TextChoices):
        FIRST_PARTY = "first_party", _("First party")
        PARTNER = "partner", _("Partner")
        THIRD_PARTY = "third_party", _("Third party")
        INTERNAL_SERVICE = "internal_service", _("Internal service")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.OneToOneField(OAuthClient, on_delete=models.CASCADE, related_name="trust_profile")
    trust_level = models.CharField(max_length=32, choices=TrustLevel.choices, default=TrustLevel.FIRST_PARTY)
    requires_pkce = models.BooleanField(default=True)
    requires_consent_screen = models.BooleanField(default=False)
    allow_offline_access = models.BooleanField(default=True)
    allow_refresh_token_rotation = models.BooleanField(default=True)
    allow_dynamic_scopes = models.BooleanField(default=False)
    max_access_token_lifetime_seconds = models.PositiveIntegerField(default=600)
    max_refresh_token_lifetime_seconds = models.PositiveIntegerField(default=1209600)
    allowed_claims = models.JSONField(default=list, blank=True)
    risk_notes = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_oauth_trust_profiles")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["trust_level"]), models.Index(fields=["requires_consent_screen"])]

    def __str__(self):
        return f"{self.client.client_id}:{self.trust_level}"

    def mark_reviewed(self, user):
        self.reviewed_by = user
        self.reviewed_at = timezone.now()
        self.save(update_fields=["reviewed_by", "reviewed_at", "updated_at"])


class OidcRefreshTokenPolicy(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.OneToOneField(OAuthClient, on_delete=models.CASCADE, related_name="refresh_token_policy")
    rotate_on_use = models.BooleanField(default=True)
    reuse_detection_enabled = models.BooleanField(default=True)
    revoke_family_on_reuse = models.BooleanField(default=True)
    idle_timeout_seconds = models.PositiveIntegerField(default=2592000)
    absolute_lifetime_seconds = models.PositiveIntegerField(default=7776000)
    sender_constrained_required = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "OIDC refresh token policy"
        verbose_name_plural = "OIDC refresh token policies"

    def __str__(self):
        return f"refresh-policy:{self.client.client_id}"


class OAuthConsentGrant(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", _("Active")
        REVOKED = "revoked", _("Revoked")
        EXPIRED = "expired", _("Expired")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="oauth_consent_grants")
    client = models.ForeignKey(OAuthClient, on_delete=models.CASCADE, related_name="consent_grants")
    scopes = models.JSONField(default=list)
    claims = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    consented_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-consented_at"]
        indexes = [models.Index(fields=["user", "client", "status"]), models.Index(fields=["client", "status"]), models.Index(fields=["expires_at"])]

    def __str__(self):
        return f"consent:{self.user_id}:{self.client_id}:{self.status}"

    def revoke(self):
        self.status = self.Status.REVOKED
        self.revoked_at = timezone.now()
        self.save(update_fields=["status", "revoked_at", "updated_at"])


class OidcTokenExchangePolicy(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.OneToOneField(OAuthClient, on_delete=models.CASCADE, related_name="token_exchange_policy")
    require_pkce_for_public_clients = models.BooleanField(default=True)
    require_nonce_for_id_token = models.BooleanField(default=True)
    allowed_grant_types = models.JSONField(default=list, blank=True)
    allowed_response_types = models.JSONField(default=list, blank=True)
    require_exact_redirect_uri = models.BooleanField(default=True)
    reject_plain_pkce = models.BooleanField(default=True)
    require_consent_for_new_scopes = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "OIDC token exchange policy"
        verbose_name_plural = "OIDC token exchange policies"

    def __str__(self):
        return f"exchange-policy:{self.client.client_id}"


class OidcDiscoveryMetadataSnapshot(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    issuer = models.URLField()
    authorization_endpoint = models.URLField()
    token_endpoint = models.URLField()
    jwks_uri = models.URLField()
    userinfo_endpoint = models.URLField(blank=True)
    scopes_supported = models.JSONField(default=list)
    claims_supported = models.JSONField(default=list)
    response_types_supported = models.JSONField(default=list)
    grant_types_supported = models.JSONField(default=list)
    signing_alg_values_supported = models.JSONField(default=list)
    metadata = models.JSONField(default=dict, blank=True)
    generated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="generated_oidc_metadata_snapshots")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["issuer"]), models.Index(fields=["created_at"])]

    def __str__(self):
        return f"oidc-metadata:{self.issuer}:{self.created_at:%Y-%m-%d}"
