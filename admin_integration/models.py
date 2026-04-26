import uuid

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class AdminApiScope(models.Model):
    class Risk(models.TextChoices):
        LOW = "low", _("Low")
        MEDIUM = "medium", _("Medium")
        HIGH = "high", _("High")
        CRITICAL = "critical", _("Critical")

    code = models.CharField(max_length=120, unique=True)
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    risk = models.CharField(max_length=16, choices=Risk.choices, default=Risk.MEDIUM)
    requires_two_person_approval = models.BooleanField(default=False)
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["code"]
        indexes = [models.Index(fields=["risk", "enabled"])]

    def __str__(self):
        return self.code


class AdminServiceCredential(models.Model):
    """Service credential used by the separate admin-control backend."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=180)
    key_prefix = models.CharField(max_length=20, unique=True)
    key_hash = models.CharField(max_length=256)
    signing_key_id = models.CharField(max_length=64, unique=True)
    signing_secret = models.CharField(max_length=256, help_text="Use encrypted/KMS storage in production.")
    scopes = models.CharField(max_length=1000, default="admin:readiness admin:read")
    allowed_ips = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="created_admin_service_credentials")
    rotated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [models.Index(fields=["key_prefix"]), models.Index(fields=["signing_key_id"]), models.Index(fields=["is_active", "expires_at"])]

    def __str__(self):
        return f"{self.name} ({self.key_prefix})"

    @property
    def scope_set(self):
        return {scope for scope in self.scopes.split() if scope}

    @property
    def is_expired(self):
        return self.expires_at is not None and timezone.now() >= self.expires_at

    def verify_key(self, raw_key):
        return check_password(raw_key, self.key_hash)

    def set_key(self, raw_key):
        self.key_hash = make_password(raw_key)
        self.key_prefix = raw_key[:20]

    def mark_used(self):
        self.last_used_at = timezone.now()
        self.save(update_fields=["last_used_at", "updated_at"])


class AdminRequestAudit(models.Model):
    class Decision(models.TextChoices):
        ALLOWED = "allowed", _("Allowed")
        DENIED = "denied", _("Denied")
        UNSIGNED = "unsigned", _("Unsigned")
        ERROR = "error", _("Error")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    credential = models.ForeignKey(AdminServiceCredential, on_delete=models.SET_NULL, null=True, blank=True, related_name="request_audits")
    key_prefix = models.CharField(max_length=20, blank=True)
    method = models.CharField(max_length=12)
    path = models.CharField(max_length=600)
    query_string_hash = models.CharField(max_length=64, blank=True)
    body_hash = models.CharField(max_length=64, blank=True)
    nonce = models.CharField(max_length=128, blank=True)
    timestamp = models.CharField(max_length=64, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    decision = models.CharField(max_length=16, choices=Decision.choices, default=Decision.UNSIGNED)
    status_code = models.PositiveIntegerField(null=True, blank=True)
    latency_ms = models.PositiveIntegerField(null=True, blank=True)
    error = models.CharField(max_length=500, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["credential", "created_at"]), models.Index(fields=["decision", "created_at"]), models.Index(fields=["path", "created_at"])]

    def __str__(self):
        return f"{self.method} {self.path} {self.decision}"


class AdminApiContractEndpoint(models.Model):
    class Domain(models.TextChoices):
        AUTH = "auth", _("Auth")
        BILLING = "billing", _("Billing")
        TENANCY = "tenancy", _("Tenancy")
        SECURITY = "security", _("Security")
        OPS = "ops", _("Operations")
        ADMIN_CONSOLE = "admin_console", _("Admin Console")
        PORTAL = "portal", _("Customer Portal")
        OBSERVABILITY = "observability", _("Observability")
        OTHER = "other", _("Other")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    domain = models.CharField(max_length=32, choices=Domain.choices)
    method = models.CharField(max_length=12)
    path = models.CharField(max_length=300)
    required_scope = models.CharField(max_length=120, blank=True)
    description = models.TextField(blank=True)
    stable = models.BooleanField(default=True)
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["domain", "path", "method"]
        constraints = [models.UniqueConstraint(fields=["method", "path"], name="unique_admin_contract_method_path")]
        indexes = [models.Index(fields=["domain", "enabled"]), models.Index(fields=["required_scope"])]

    def __str__(self):
        return f"{self.method} {self.path}"


class AdminIntegrationReadinessSnapshot(models.Model):
    status = models.CharField(max_length=32)
    checks = models.JSONField(default=list)
    metadata = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "created_at"])]
