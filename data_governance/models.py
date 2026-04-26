from __future__ import annotations

import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone


class DataSensitivity(models.TextChoices):
    PUBLIC = "public", "Public"
    INTERNAL = "internal", "Internal"
    CONFIDENTIAL = "confidential", "Confidential"
    RESTRICTED = "restricted", "Restricted"


class ProcessingBasis(models.TextChoices):
    CONTRACT = "contract", "Contract"
    CONSENT = "consent", "Consent"
    LEGITIMATE_INTEREST = "legitimate_interest", "Legitimate interest"
    LEGAL_OBLIGATION = "legal_obligation", "Legal obligation"
    SECURITY = "security", "Security"


class GovernanceStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    ACTIVE = "active", "Active"
    PAUSED = "paused", "Paused"
    RETIRED = "retired", "Retired"


class DataCategory(models.Model):
    """Classification catalog entry for PII and operational data categories."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    key = models.SlugField(max_length=120, unique=True)
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    sensitivity = models.CharField(max_length=24, choices=DataSensitivity.choices, default=DataSensitivity.INTERNAL)
    processing_basis = models.CharField(max_length=32, choices=ProcessingBasis.choices, default=ProcessingBasis.CONTRACT)
    is_pii = models.BooleanField(default=False)
    is_payment_data = models.BooleanField(default=False)
    default_retention_days = models.PositiveIntegerField(default=365)
    default_anonymization_strategy = models.CharField(max_length=80, default="hash_or_null")
    owner_team = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=16, choices=GovernanceStatus.choices, default=GovernanceStatus.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["key"]

    def __str__(self):
        return self.key


class DataAsset(models.Model):
    """A table, API resource, provider object, export bucket, or log stream holding data."""

    class AssetType(models.TextChoices):
        MODEL = "model", "Django model"
        TABLE = "table", "Database table"
        API = "api", "API endpoint"
        PROVIDER = "provider", "Payment/notification provider object"
        FILE = "file", "File/export storage"
        LOG = "log", "Log/observability stream"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    key = models.SlugField(max_length=160, unique=True)
    name = models.CharField(max_length=180)
    asset_type = models.CharField(max_length=24, choices=AssetType.choices, default=AssetType.MODEL)
    app_label = models.CharField(max_length=80, blank=True)
    model_name = models.CharField(max_length=120, blank=True)
    storage_location = models.CharField(max_length=240, blank=True)
    categories = models.ManyToManyField(DataCategory, related_name="assets", blank=True)
    contains_pii = models.BooleanField(default=False)
    contains_payment_data = models.BooleanField(default=False)
    encryption_required = models.BooleanField(default=True)
    access_review_required = models.BooleanField(default=True)
    owner_team = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=16, choices=GovernanceStatus.choices, default=GovernanceStatus.ACTIVE)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["app_label", "key"]

    def __str__(self):
        return self.key


class RetentionPolicy(models.Model):
    """Retention and disposal policy attached to one or more assets/categories."""

    class Action(models.TextChoices):
        DELETE = "delete", "Delete"
        ANONYMIZE = "anonymize", "Anonymize"
        ARCHIVE = "archive", "Archive"
        REVIEW = "review", "Review"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    key = models.SlugField(max_length=160, unique=True)
    name = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    assets = models.ManyToManyField(DataAsset, related_name="retention_policies", blank=True)
    categories = models.ManyToManyField(DataCategory, related_name="retention_policies", blank=True)
    retention_days = models.PositiveIntegerField(default=365)
    action = models.CharField(max_length=16, choices=Action.choices, default=Action.ANONYMIZE)
    grace_days = models.PositiveIntegerField(default=30)
    legal_hold_exempt = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    owner_team = models.CharField(max_length=120, blank=True)
    runbook_url = models.CharField(max_length=500, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="retention_policies_created")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["key"]

    def __str__(self):
        return self.key


class LegalHold(models.Model):
    """Prevents automated deletion/anonymization for users, organizations, or data classes."""

    class Scope(models.TextChoices):
        USER = "user", "User"
        ORGANIZATION = "organization", "Organization"
        CATEGORY = "category", "Data category"
        GLOBAL = "global", "Global"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        RELEASED = "released", "Released"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scope = models.CharField(max_length=24, choices=Scope.choices)
    reason = models.CharField(max_length=240)
    description = models.TextField(blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE, related_name="legal_holds")
    organization = models.ForeignKey("accounts.Organization", null=True, blank=True, on_delete=models.CASCADE, related_name="legal_holds")
    category = models.ForeignKey(DataCategory, null=True, blank=True, on_delete=models.CASCADE, related_name="legal_holds")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    starts_at = models.DateTimeField(default=timezone.now)
    ends_at = models.DateTimeField(null=True, blank=True)
    released_at = models.DateTimeField(null=True, blank=True)
    released_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="legal_holds_released")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="legal_holds_created")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def is_current(self) -> bool:
        now = timezone.now()
        return self.status == self.Status.ACTIVE and self.starts_at <= now and (self.ends_at is None or self.ends_at > now)


class DataSubjectRequest(models.Model):
    """Governed access/export/delete/correct/restrict request for a user or organization."""

    class RequestType(models.TextChoices):
        ACCESS = "access", "Access"
        EXPORT = "export", "Export"
        DELETE = "delete", "Delete"
        CORRECT = "correct", "Correct"
        RESTRICT = "restrict", "Restrict processing"
        OBJECT = "object", "Object to processing"

    class Status(models.TextChoices):
        RECEIVED = "received", "Received"
        VERIFYING = "verifying", "Verifying identity"
        APPROVED = "approved", "Approved"
        IN_PROGRESS = "in_progress", "In progress"
        COMPLETED = "completed", "Completed"
        REJECTED = "rejected", "Rejected"
        BLOCKED_BY_HOLD = "blocked_by_hold", "Blocked by legal hold"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    request_type = models.CharField(max_length=16, choices=RequestType.choices)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.RECEIVED)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE, related_name="data_subject_requests")
    organization = models.ForeignKey("accounts.Organization", null=True, blank=True, on_delete=models.CASCADE, related_name="data_subject_requests")
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="data_subject_requests_opened")
    verification_notes = models.TextField(blank=True)
    scope = models.JSONField(default=dict, blank=True)
    due_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    evidence_checksum = models.CharField(max_length=128, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]


class RetentionJob(models.Model):
    """Operational job record for retention scans and anonymization/deletion batches."""

    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        BLOCKED = "blocked", "Blocked"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    policy = models.ForeignKey(RetentionPolicy, on_delete=models.CASCADE, related_name="jobs")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.QUEUED)
    dry_run = models.BooleanField(default=True)
    cutoff_at = models.DateTimeField()
    candidate_count = models.PositiveIntegerField(default=0)
    processed_count = models.PositiveIntegerField(default=0)
    blocked_count = models.PositiveIntegerField(default=0)
    result_summary = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="retention_jobs_created")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class AnonymizationRecord(models.Model):
    """Append-only record of anonymization/delete actions. Store metadata, never raw PII."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey(RetentionJob, null=True, blank=True, on_delete=models.SET_NULL, related_name="anonymization_records")
    asset = models.ForeignKey(DataAsset, null=True, blank=True, on_delete=models.SET_NULL, related_name="anonymization_records")
    subject_type = models.CharField(max_length=80)
    subject_id_hash = models.CharField(max_length=128)
    action = models.CharField(max_length=24)
    fields_changed = models.JSONField(default=list, blank=True)
    checksum_before = models.CharField(max_length=128, blank=True)
    checksum_after = models.CharField(max_length=128, blank=True)
    performed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="anonymization_records_performed")
    performed_at = models.DateTimeField(default=timezone.now)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-performed_at"]


class DataInventorySnapshot(models.Model):
    """Point-in-time governance summary for audits and compliance evidence packs."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    generated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="data_inventory_snapshots")
    asset_count = models.PositiveIntegerField(default=0)
    pii_asset_count = models.PositiveIntegerField(default=0)
    restricted_asset_count = models.PositiveIntegerField(default=0)
    active_policy_count = models.PositiveIntegerField(default=0)
    active_legal_hold_count = models.PositiveIntegerField(default=0)
    open_subject_request_count = models.PositiveIntegerField(default=0)
    summary = models.JSONField(default=dict, blank=True)
    generated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-generated_at"]
