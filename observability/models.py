from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class ObservabilitySeverity(models.TextChoices):
    DEBUG = "debug", "Debug"
    INFO = "info", "Info"
    WARNING = "warning", "Warning"
    ERROR = "error", "Error"
    CRITICAL = "critical", "Critical"


class ApplicationEvent(models.Model):
    """Structured application event for auth, billing, security, ops, and first-party apps."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_type = models.CharField(max_length=160)
    source_app = models.CharField(max_length=80, default="auth-platform")
    severity = models.CharField(max_length=16, choices=ObservabilitySeverity.choices, default=ObservabilitySeverity.INFO)
    organization = models.ForeignKey("accounts.Organization", on_delete=models.SET_NULL, null=True, blank=True, related_name="application_events")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="application_events")
    request_id = models.CharField(max_length=120, blank=True, db_index=True)
    trace_id = models.CharField(max_length=120, blank=True, db_index=True)
    span_id = models.CharField(max_length=120, blank=True)
    subject_type = models.CharField(max_length=80, blank=True)
    subject_id = models.CharField(max_length=160, blank=True)
    message = models.TextField(blank=True)
    payload = models.JSONField(default=dict, blank=True)
    occurred_at = models.DateTimeField(default=timezone.now, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-occurred_at"]
        indexes = [
            models.Index(fields=["event_type", "occurred_at"]),
            models.Index(fields=["source_app", "severity", "occurred_at"]),
            models.Index(fields=["organization", "occurred_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.source_app}:{self.event_type}:{self.severity}"


class MetricSnapshot(models.Model):
    """Time-bucketed metric snapshot for dashboards and SLO calculations."""

    class Kind(models.TextChoices):
        COUNTER = "counter", "Counter"
        GAUGE = "gauge", "Gauge"
        HISTOGRAM = "histogram", "Histogram"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=160)
    kind = models.CharField(max_length=16, choices=Kind.choices, default=Kind.GAUGE)
    source_app = models.CharField(max_length=80, default="auth-platform")
    value = models.DecimalField(max_digits=20, decimal_places=6)
    unit = models.CharField(max_length=32, blank=True)
    dimensions = models.JSONField(default=dict, blank=True)
    bucket_start = models.DateTimeField(default=timezone.now, db_index=True)
    bucket_seconds = models.PositiveIntegerField(default=60)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-bucket_start", "name"]
        indexes = [models.Index(fields=["name", "bucket_start"]), models.Index(fields=["source_app", "bucket_start"])]
        unique_together = [("name", "source_app", "bucket_start", "bucket_seconds")]

    def __str__(self) -> str:
        return f"{self.name}={self.value} {self.unit}".strip()


class TraceSample(models.Model):
    """Request trace metadata for debugging slow/error-prone auth and billing flows."""

    class Status(models.TextChoices):
        OK = "ok", "OK"
        ERROR = "error", "Error"
        TIMEOUT = "timeout", "Timeout"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    trace_id = models.CharField(max_length=120, db_index=True)
    request_id = models.CharField(max_length=120, blank=True, db_index=True)
    method = models.CharField(max_length=12, blank=True)
    path = models.CharField(max_length=500)
    status_code = models.PositiveIntegerField(default=0)
    duration_ms = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.OK)
    source_app = models.CharField(max_length=80, default="auth-platform")
    organization = models.ForeignKey("accounts.Organization", on_delete=models.SET_NULL, null=True, blank=True, related_name="trace_samples")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="trace_samples")
    metadata = models.JSONField(default=dict, blank=True)
    started_at = models.DateTimeField(default=timezone.now, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-started_at"]
        indexes = [models.Index(fields=["path", "status_code", "started_at"]), models.Index(fields=["source_app", "started_at"])]

    def __str__(self) -> str:
        return f"{self.method} {self.path} {self.status_code} {self.duration_ms}ms"


class ServiceLevelObjective(models.Model):
    """SLO definition for critical journeys such as login, checkout, webhook handling, and API auth."""

    class Window(models.TextChoices):
        DAY_7 = "7d", "7 days"
        DAY_30 = "30d", "30 days"
        DAY_90 = "90d", "90 days"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=160, unique=True)
    source_app = models.CharField(max_length=80, default="auth-platform")
    target_percentage = models.DecimalField(max_digits=6, decimal_places=3, default=99.900)
    window = models.CharField(max_length=8, choices=Window.choices, default=Window.DAY_30)
    good_events_query = models.JSONField(default=dict, blank=True)
    total_events_query = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    owner_team = models.CharField(max_length=120, blank=True)
    runbook_url = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} {self.target_percentage}%"


class SLOSnapshot(models.Model):
    slo = models.ForeignKey(ServiceLevelObjective, on_delete=models.CASCADE, related_name="snapshots")
    measured_percentage = models.DecimalField(max_digits=7, decimal_places=4)
    good_events = models.PositiveBigIntegerField(default=0)
    total_events = models.PositiveBigIntegerField(default=0)
    error_budget_remaining = models.DecimalField(max_digits=7, decimal_places=4, default=100)
    window_start = models.DateTimeField()
    window_end = models.DateTimeField(default=timezone.now)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-window_end"]
        indexes = [models.Index(fields=["slo", "window_end"])]

    def __str__(self) -> str:
        return f"{self.slo.name}: {self.measured_percentage}%"


class AlertRule(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        MUTED = "muted", "Muted"
        DISABLED = "disabled", "Disabled"

    class Comparator(models.TextChoices):
        GT = "gt", ">"
        GTE = "gte", ">="
        LT = "lt", "<"
        LTE = "lte", "<="
        EQ = "eq", "="

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=160, unique=True)
    metric_name = models.CharField(max_length=160)
    comparator = models.CharField(max_length=8, choices=Comparator.choices, default=Comparator.GTE)
    threshold = models.DecimalField(max_digits=20, decimal_places=6)
    severity = models.CharField(max_length=16, choices=ObservabilitySeverity.choices, default=ObservabilitySeverity.ERROR)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    evaluation_window_seconds = models.PositiveIntegerField(default=300)
    notify_channels = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    last_triggered_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="alert_rules_created")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class AlertIncident(models.Model):
    class State(models.TextChoices):
        OPEN = "open", "Open"
        ACKNOWLEDGED = "acknowledged", "Acknowledged"
        RESOLVED = "resolved", "Resolved"
        SUPPRESSED = "suppressed", "Suppressed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rule = models.ForeignKey(AlertRule, on_delete=models.PROTECT, related_name="incidents")
    state = models.CharField(max_length=24, choices=State.choices, default=State.OPEN)
    severity = models.CharField(max_length=16, choices=ObservabilitySeverity.choices, default=ObservabilitySeverity.ERROR)
    title = models.CharField(max_length=240)
    description = models.TextField(blank=True)
    triggered_value = models.DecimalField(max_digits=20, decimal_places=6, null=True, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    opened_at = models.DateTimeField(default=timezone.now)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    acknowledged_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="alert_incidents_acknowledged")
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="alert_incidents_resolved")

    class Meta:
        ordering = ["-opened_at"]
        indexes = [models.Index(fields=["state", "severity", "opened_at"])]

    def __str__(self) -> str:
        return self.title
