from rest_framework import serializers

from .models import AlertIncident, AlertRule, ApplicationEvent, MetricSnapshot, SLOSnapshot, ServiceLevelObjective, TraceSample
from .services import acknowledge_alert, calculate_slo_snapshot, resolve_alert


class ApplicationEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApplicationEvent
        fields = ["id", "event_type", "source_app", "severity", "organization", "user", "request_id", "trace_id", "span_id", "subject_type", "subject_id", "message", "payload", "occurred_at", "created_at"]
        read_only_fields = ["id", "created_at"]


class MetricSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = MetricSnapshot
        fields = ["id", "name", "kind", "source_app", "value", "unit", "dimensions", "bucket_start", "bucket_seconds", "created_at"]
        read_only_fields = ["id", "created_at"]


class TraceSampleSerializer(serializers.ModelSerializer):
    class Meta:
        model = TraceSample
        fields = ["id", "trace_id", "request_id", "method", "path", "status_code", "duration_ms", "status", "source_app", "organization", "user", "metadata", "started_at", "created_at"]
        read_only_fields = ["id", "created_at"]


class ServiceLevelObjectiveSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceLevelObjective
        fields = ["id", "name", "source_app", "target_percentage", "window", "good_events_query", "total_events_query", "is_active", "owner_team", "runbook_url", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class SLOSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = SLOSnapshot
        fields = ["id", "slo", "measured_percentage", "good_events", "total_events", "error_budget_remaining", "window_start", "window_end", "notes", "created_at"]
        read_only_fields = ["id", "created_at"]


class SLOCalculateSerializer(serializers.Serializer):
    def save(self, **kwargs):
        return calculate_slo_snapshot(self.context["slo"])


class AlertRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = AlertRule
        fields = ["id", "name", "metric_name", "comparator", "threshold", "severity", "status", "evaluation_window_seconds", "notify_channels", "metadata", "last_triggered_at", "created_by", "created_at", "updated_at"]
        read_only_fields = ["id", "last_triggered_at", "created_by", "created_at", "updated_at"]

    def create(self, validated_data):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["created_by"] = request.user
        return super().create(validated_data)


class AlertIncidentSerializer(serializers.ModelSerializer):
    class Meta:
        model = AlertIncident
        fields = ["id", "rule", "state", "severity", "title", "description", "triggered_value", "payload", "opened_at", "acknowledged_at", "acknowledged_by", "resolved_at", "resolved_by"]
        read_only_fields = ["id", "opened_at", "acknowledged_at", "acknowledged_by", "resolved_at", "resolved_by"]


class AlertActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["acknowledge", "resolve", "suppress"])

    def save(self, **kwargs):
        incident = self.context["incident"]
        user = self.context["request"].user
        action = self.validated_data["action"]
        if action == "acknowledge":
            return acknowledge_alert(incident, user)
        if action == "resolve":
            return resolve_alert(incident, user)
        incident.state = AlertIncident.State.SUPPRESSED
        incident.save(update_fields=["state"])
        return incident
