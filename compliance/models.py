import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class PolicyDocument(models.Model):
    """Versioned legal/security policy that users or staff may need to accept."""

    class PolicyType(models.TextChoices):
        TERMS = "terms", _("Terms of service")
        PRIVACY = "privacy", _("Privacy policy")
        DPA = "dpa", _("Data processing addendum")
        AUP = "aup", _("Acceptable use policy")
        SECURITY = "security", _("Security policy")
        BILLING = "billing", _("Billing policy")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    policy_type = models.CharField(max_length=32, choices=PolicyType.choices)
    version = models.CharField(max_length=40)
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True)
    document_url = models.URLField(blank=True)
    checksum_sha256 = models.CharField(max_length=64, blank=True)
    requires_user_acceptance = models.BooleanField(default=True)
    requires_admin_acceptance = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    retired_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="created_policy_documents")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("policy_type", "version")]
        ordering = ["policy_type", "-published_at", "-created_at"]
        indexes = [
            models.Index(fields=["policy_type", "is_active"]),
            models.Index(fields=["version"]),
            models.Index(fields=["published_at"]),
        ]

    def __str__(self):
        return f"{self.policy_type}:{self.version}"

    def publish(self, actor=None):
        if not self.published_at:
            self.published_at = timezone.now()
        self.is_active = True
        if actor and not self.created_by_id:
            self.created_by = actor
        self.save(update_fields=["published_at", "is_active", "created_by", "updated_at"])


class UserPolicyAcceptance(models.Model):
    """Immutable-ish acceptance record for user/admin policy versions."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="policy_acceptances")
    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, null=True, blank=True, related_name="policy_acceptances")
    policy = models.ForeignKey(PolicyDocument, on_delete=models.PROTECT, related_name="acceptances")
    accepted_at = models.DateTimeField(default=timezone.now)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = [("user", "organization", "policy")]
        ordering = ["-accepted_at"]
        indexes = [
            models.Index(fields=["user", "accepted_at"]),
            models.Index(fields=["organization", "accepted_at"]),
            models.Index(fields=["policy", "accepted_at"]),
        ]

    def __str__(self):
        return f"{self.user_id}:{self.policy_id}:{self.accepted_at.isoformat()}"


class AdminApprovalRequest(models.Model):
    """Two-person approval workflow for high-risk admin actions."""

    class ActionType(models.TextChoices):
        BILLING_OVERRIDE = "billing_override", _("Billing override")
        SECURITY_RESTRICTION = "security_restriction", _("Security restriction")
        USER_EXPORT = "user_export", _("User data export")
        ACCOUNT_DELETION = "account_deletion", _("Account deletion")
        POLICY_PUBLISH = "policy_publish", _("Policy publish")
        PROVIDER_REPLAY = "provider_replay", _("Webhook/provider replay")
        SERVICE_KEY_ROTATION = "service_key_rotation", _("Service key rotation")

    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        APPROVED = "approved", _("Approved")
        REJECTED = "rejected", _("Rejected")
        CANCELLED = "cancelled", _("Cancelled")
        EXPIRED = "expired", _("Expired")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    action_type = models.CharField(max_length=40, choices=ActionType.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="approval_requests_created")
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="approval_requests_reviewed")
    organization = models.ForeignKey("accounts.Organization", on_delete=models.SET_NULL, null=True, blank=True, related_name="approval_requests")
    subject_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="approval_requests_about_user")
    summary = models.CharField(max_length=255)
    reason = models.TextField(blank=True)
    payload = models.JSONField(default=dict, blank=True)
    review_notes = models.TextField(blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["action_type", "status"]),
            models.Index(fields=["requested_by", "status"]),
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["expires_at"]),
        ]

    def __str__(self):
        return f"{self.action_type}:{self.status}:{self.summary}"

    @property
    def is_expired(self):
        return self.expires_at is not None and timezone.now() >= self.expires_at

    def approve(self, reviewer, notes=""):
        if reviewer and reviewer.pk == self.requested_by_id:
            raise ValueError("The requester cannot approve their own request.")
        self.status = self.Status.APPROVED
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.review_notes = notes
        self.save(update_fields=["status", "reviewed_by", "reviewed_at", "review_notes", "updated_at"])

    def reject(self, reviewer, notes=""):
        self.status = self.Status.REJECTED
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.review_notes = notes
        self.save(update_fields=["status", "reviewed_by", "reviewed_at", "review_notes", "updated_at"])


class AuditExport(models.Model):
    """Tamper-evident export request metadata for audit, billing, and security evidence."""

    class ExportType(models.TextChoices):
        AUDIT_LOG = "audit_log", _("Audit log")
        SECURITY_EVENTS = "security_events", _("Security events")
        BILLING_EVENTS = "billing_events", _("Billing events")
        POLICY_ACCEPTANCES = "policy_acceptances", _("Policy acceptances")
        FULL_EVIDENCE = "full_evidence", _("Full evidence")

    class Status(models.TextChoices):
        REQUESTED = "requested", _("Requested")
        READY = "ready", _("Ready")
        FAILED = "failed", _("Failed")
        EXPIRED = "expired", _("Expired")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    export_type = models.CharField(max_length=40, choices=ExportType.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.REQUESTED)
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="audit_exports")
    organization = models.ForeignKey("accounts.Organization", on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_exports")
    date_from = models.DateTimeField(null=True, blank=True)
    date_to = models.DateTimeField(null=True, blank=True)
    storage_uri = models.CharField(max_length=500, blank=True)
    checksum_sha256 = models.CharField(max_length=64, blank=True)
    record_count = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["export_type", "status"]),
            models.Index(fields=["organization", "created_at"]),
            models.Index(fields=["expires_at"]),
        ]

    def __str__(self):
        return f"{self.export_type}:{self.status}:{self.id}"

    def mark_ready(self, storage_uri, checksum_sha256, record_count):
        self.status = self.Status.READY
        self.storage_uri = storage_uri
        self.checksum_sha256 = checksum_sha256
        self.record_count = record_count
        self.completed_at = timezone.now()
        self.save(update_fields=["status", "storage_uri", "checksum_sha256", "record_count", "completed_at"])


class EvidencePack(models.Model):
    """Grouped evidence bundle for audits, disputes, incident response, and compliance reviews."""

    class PackType(models.TextChoices):
        SECURITY_INCIDENT = "security_incident", _("Security incident")
        BILLING_DISPUTE = "billing_dispute", _("Billing dispute")
        CUSTOMER_AUDIT = "customer_audit", _("Customer audit")
        COMPLIANCE_REVIEW = "compliance_review", _("Compliance review")

    class Status(models.TextChoices):
        DRAFT = "draft", _("Draft")
        LOCKED = "locked", _("Locked")
        EXPORTED = "exported", _("Exported")
        ARCHIVED = "archived", _("Archived")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pack_type = models.CharField(max_length=40, choices=PackType.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    title = models.CharField(max_length=220)
    organization = models.ForeignKey("accounts.Organization", on_delete=models.SET_NULL, null=True, blank=True, related_name="evidence_packs")
    subject_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="evidence_packs")
    security_incident = models.ForeignKey("security_ops.SecurityIncident", on_delete=models.SET_NULL, null=True, blank=True, related_name="evidence_packs")
    audit_exports = models.ManyToManyField(AuditExport, blank=True, related_name="evidence_packs")
    summary = models.TextField(blank=True)
    evidence_index = models.JSONField(default=list, blank=True)
    locked_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="locked_evidence_packs")
    locked_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="created_evidence_packs")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["pack_type", "status"]),
            models.Index(fields=["organization", "created_at"]),
            models.Index(fields=["subject_user", "created_at"]),
        ]

    def __str__(self):
        return f"{self.pack_type}:{self.title}"

    def lock(self, actor):
        if self.status == self.Status.DRAFT:
            self.status = self.Status.LOCKED
            self.locked_by = actor
            self.locked_at = timezone.now()
            self.save(update_fields=["status", "locked_by", "locked_at", "updated_at"])
