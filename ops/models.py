from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone


class EnvironmentCheck(models.Model):
    class Status(models.TextChoices):
        PASS = "pass", "Pass"
        WARN = "warn", "Warn"
        FAIL = "fail", "Fail"

    key = models.CharField(max_length=160, unique=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.WARN)
    message = models.TextField(blank=True)
    details = models.JSONField(default=dict, blank=True)
    checked_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["key"]

    def __str__(self) -> str:
        return f"{self.key}: {self.status}"


class ServiceHealthCheck(models.Model):
    class Status(models.TextChoices):
        HEALTHY = "healthy", "Healthy"
        DEGRADED = "degraded", "Degraded"
        DOWN = "down", "Down"
        UNKNOWN = "unknown", "Unknown"

    name = models.CharField(max_length=120, unique=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.UNKNOWN)
    latency_ms = models.PositiveIntegerField(default=0)
    message = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    checked_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name}: {self.status}"


class MaintenanceWindow(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    title = models.CharField(max_length=180)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.SCHEDULED)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    affected_services = models.JSONField(default=list, blank=True)
    customer_message = models.TextField(blank=True)
    internal_notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="maintenance_windows_created")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-starts_at"]

    def __str__(self) -> str:
        return self.title

    @property
    def is_current(self) -> bool:
        now = timezone.now()
        return self.status == self.Status.ACTIVE and self.starts_at <= now <= self.ends_at


class BackupSnapshot(models.Model):
    class Status(models.TextChoices):
        REQUESTED = "requested", "Requested"
        RUNNING = "running", "Running"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        RESTORED = "restored", "Restored"

    label = models.CharField(max_length=180)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.REQUESTED)
    database_name = models.CharField(max_length=120, default="default")
    storage_uri = models.CharField(max_length=500, blank=True)
    checksum_sha256 = models.CharField(max_length=64, blank=True)
    size_bytes = models.PositiveBigIntegerField(default=0)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="backup_snapshots_requested")
    metadata = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.label


class RestoreRun(models.Model):
    class Status(models.TextChoices):
        PLANNED = "planned", "Planned"
        APPROVED = "approved", "Approved"
        RUNNING = "running", "Running"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    backup = models.ForeignKey(BackupSnapshot, on_delete=models.PROTECT, related_name="restore_runs")
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.PLANNED)
    target_environment = models.CharField(max_length=80, default="staging")
    reason = models.TextField()
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="restore_runs_requested")
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="restore_runs_approved")
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    result_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Restore {self.backup_id} to {self.target_environment}"


class StatusIncident(models.Model):
    class Impact(models.TextChoices):
        NONE = "none", "None"
        MINOR = "minor", "Minor"
        MAJOR = "major", "Major"
        CRITICAL = "critical", "Critical"

    class State(models.TextChoices):
        INVESTIGATING = "investigating", "Investigating"
        IDENTIFIED = "identified", "Identified"
        MONITORING = "monitoring", "Monitoring"
        RESOLVED = "resolved", "Resolved"

    title = models.CharField(max_length=180)
    state = models.CharField(max_length=24, choices=State.choices, default=State.INVESTIGATING)
    impact = models.CharField(max_length=16, choices=Impact.choices, default=Impact.MINOR)
    affected_services = models.JSONField(default=list, blank=True)
    public_message = models.TextField(blank=True)
    internal_notes = models.TextField(blank=True)
    started_at = models.DateTimeField(default=timezone.now)
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="status_incidents_created")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self) -> str:
        return self.title


class ReleaseRecord(models.Model):
    class Status(models.TextChoices):
        PLANNED = "planned", "Planned"
        STAGED = "staged", "Staged"
        RELEASED = "released", "Released"
        ROLLED_BACK = "rolled_back", "Rolled back"
        FAILED = "failed", "Failed"

    version = models.CharField(max_length=40, unique=True)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.PLANNED)
    git_sha = models.CharField(max_length=80, blank=True)
    image_tag = models.CharField(max_length=160, blank=True)
    changelog = models.TextField(blank=True)
    deployed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="releases_deployed")
    deployed_at = models.DateTimeField(null=True, blank=True)
    rollback_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.version
