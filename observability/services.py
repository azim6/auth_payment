from __future__ import annotations

from decimal import Decimal

from django.db.models import Avg, Count
from django.utils import timezone

from .models import AlertIncident, AlertRule, ApplicationEvent, MetricSnapshot, ObservabilitySeverity, SLOSnapshot, ServiceLevelObjective, TraceSample


def record_event(*, event_type: str, source_app: str = "auth-platform", severity: str = ObservabilitySeverity.INFO, **kwargs) -> ApplicationEvent:
    return ApplicationEvent.objects.create(event_type=event_type, source_app=source_app, severity=severity, **kwargs)


def record_metric(*, name: str, value, source_app: str = "auth-platform", kind: str = MetricSnapshot.Kind.GAUGE, unit: str = "", dimensions: dict | None = None) -> MetricSnapshot:
    return MetricSnapshot.objects.create(name=name, value=value, source_app=source_app, kind=kind, unit=unit, dimensions=dimensions or {})


def build_observability_summary() -> dict:
    now = timezone.now()
    recent_events = ApplicationEvent.objects.filter(occurred_at__gte=now - timezone.timedelta(hours=24))
    recent_traces = TraceSample.objects.filter(started_at__gte=now - timezone.timedelta(hours=24))
    return {
        "events_24h": recent_events.count(),
        "critical_events_24h": recent_events.filter(severity=ObservabilitySeverity.CRITICAL).count(),
        "error_events_24h": recent_events.filter(severity=ObservabilitySeverity.ERROR).count(),
        "traces_24h": recent_traces.count(),
        "avg_duration_ms_24h": int(recent_traces.aggregate(avg=Avg("duration_ms"))["avg"] or 0),
        "open_alerts": AlertIncident.objects.filter(state=AlertIncident.State.OPEN).count(),
        "active_slos": ServiceLevelObjective.objects.filter(is_active=True).count(),
    }


def calculate_slo_snapshot(slo: ServiceLevelObjective) -> SLOSnapshot:
    days = {"7d": 7, "30d": 30, "90d": 90}.get(slo.window, 30)
    window_end = timezone.now()
    window_start = window_end - timezone.timedelta(days=days)
    total = ApplicationEvent.objects.filter(source_app=slo.source_app, occurred_at__gte=window_start, occurred_at__lte=window_end).count()
    bad = ApplicationEvent.objects.filter(source_app=slo.source_app, severity__in=[ObservabilitySeverity.ERROR, ObservabilitySeverity.CRITICAL], occurred_at__gte=window_start, occurred_at__lte=window_end).count()
    good = max(total - bad, 0)
    measured = Decimal("100.0000") if total == 0 else (Decimal(good) / Decimal(total) * Decimal("100")).quantize(Decimal("0.0001"))
    budget = max(Decimal("0"), measured - slo.target_percentage).quantize(Decimal("0.0001"))
    return SLOSnapshot.objects.create(slo=slo, measured_percentage=measured, good_events=good, total_events=total, error_budget_remaining=budget, window_start=window_start, window_end=window_end)


def evaluate_alert_rule(rule: AlertRule) -> AlertIncident | None:
    if rule.status != AlertRule.Status.ACTIVE:
        return None
    since = timezone.now() - timezone.timedelta(seconds=rule.evaluation_window_seconds)
    metric = MetricSnapshot.objects.filter(name=rule.metric_name, bucket_start__gte=since).order_by("-bucket_start").first()
    if not metric:
        return None
    value = metric.value
    threshold = rule.threshold
    comparisons = {
        AlertRule.Comparator.GT: value > threshold,
        AlertRule.Comparator.GTE: value >= threshold,
        AlertRule.Comparator.LT: value < threshold,
        AlertRule.Comparator.LTE: value <= threshold,
        AlertRule.Comparator.EQ: value == threshold,
    }
    if not comparisons.get(rule.comparator, False):
        return None
    rule.last_triggered_at = timezone.now()
    rule.save(update_fields=["last_triggered_at", "updated_at"])
    return AlertIncident.objects.create(rule=rule, severity=rule.severity, title=f"{rule.name} triggered", description=f"{rule.metric_name} value {value} crossed {rule.comparator} {threshold}", triggered_value=value, payload={"metric_id": str(metric.id)})


def acknowledge_alert(incident: AlertIncident, user) -> AlertIncident:
    incident.state = AlertIncident.State.ACKNOWLEDGED
    incident.acknowledged_by = user
    incident.acknowledged_at = timezone.now()
    incident.save(update_fields=["state", "acknowledged_by", "acknowledged_at"])
    return incident


def resolve_alert(incident: AlertIncident, user) -> AlertIncident:
    incident.state = AlertIncident.State.RESOLVED
    incident.resolved_by = user
    incident.resolved_at = timezone.now()
    incident.save(update_fields=["state", "resolved_by", "resolved_at"])
    return incident
