from django.contrib import admin

from .models import AlertIncident, AlertRule, ApplicationEvent, MetricSnapshot, SLOSnapshot, ServiceLevelObjective, TraceSample


@admin.register(ApplicationEvent)
class ApplicationEventAdmin(admin.ModelAdmin):
    list_display = ["event_type", "source_app", "severity", "organization", "user", "occurred_at"]
    list_filter = ["source_app", "severity", "event_type"]
    search_fields = ["event_type", "message", "request_id", "trace_id", "subject_id"]
    readonly_fields = ["id", "created_at"]


@admin.register(MetricSnapshot)
class MetricSnapshotAdmin(admin.ModelAdmin):
    list_display = ["name", "source_app", "kind", "value", "unit", "bucket_start"]
    list_filter = ["kind", "source_app"]
    search_fields = ["name"]


@admin.register(TraceSample)
class TraceSampleAdmin(admin.ModelAdmin):
    list_display = ["method", "path", "status_code", "duration_ms", "status", "started_at"]
    list_filter = ["status", "status_code", "source_app"]
    search_fields = ["trace_id", "request_id", "path"]


@admin.register(ServiceLevelObjective)
class ServiceLevelObjectiveAdmin(admin.ModelAdmin):
    list_display = ["name", "source_app", "target_percentage", "window", "is_active", "owner_team"]
    list_filter = ["is_active", "window", "source_app"]
    search_fields = ["name", "owner_team"]


@admin.register(SLOSnapshot)
class SLOSnapshotAdmin(admin.ModelAdmin):
    list_display = ["slo", "measured_percentage", "good_events", "total_events", "error_budget_remaining", "window_end"]
    list_filter = ["slo"]


@admin.register(AlertRule)
class AlertRuleAdmin(admin.ModelAdmin):
    list_display = ["name", "metric_name", "comparator", "threshold", "severity", "status", "last_triggered_at"]
    list_filter = ["status", "severity"]
    search_fields = ["name", "metric_name"]


@admin.register(AlertIncident)
class AlertIncidentAdmin(admin.ModelAdmin):
    list_display = ["title", "rule", "state", "severity", "opened_at", "resolved_at"]
    list_filter = ["state", "severity"]
    search_fields = ["title", "description"]
