from __future__ import annotations

from django.db.models import Avg
from django.utils import timezone

from .models import AlertIncident, AlertRule, ApplicationEvent, MetricSnapshot, ObservabilitySeverity, SLOSnapshot, ServiceLevelObjective, TraceSample


def _check(name: str, ok: bool, detail: str, severity: str = "warning") -> dict:
    return {"name": name, "ok": bool(ok), "severity": "ok" if ok else severity, "detail": detail}


def build_observability_readiness_report() -> dict:
    """Return an operator-facing report for telemetry, SLO, and alert readiness."""
    now = timezone.now()
    day_ago = now - timezone.timedelta(hours=24)
    week_ago = now - timezone.timedelta(days=7)

    recent_events = ApplicationEvent.objects.filter(occurred_at__gte=day_ago)
    recent_metrics = MetricSnapshot.objects.filter(bucket_start__gte=day_ago)
    recent_traces = TraceSample.objects.filter(started_at__gte=day_ago)
    active_slos = ServiceLevelObjective.objects.filter(is_active=True)
    recent_slo_snapshots = SLOSnapshot.objects.filter(window_end__gte=week_ago)
    active_alert_rules = AlertRule.objects.filter(status=AlertRule.Status.ACTIVE)
    open_alerts = AlertIncident.objects.filter(state=AlertIncident.State.OPEN)
    critical_open_alerts = open_alerts.filter(severity=ObservabilitySeverity.CRITICAL)
    avg_duration = int(recent_traces.aggregate(avg=Avg("duration_ms"))["avg"] or 0)

    checks = [
        _check("recent_application_events", recent_events.exists(), f"{recent_events.count()} application event(s) recorded in the last 24h."),
        _check("recent_metrics", recent_metrics.exists(), f"{recent_metrics.count()} metric snapshot(s) recorded in the last 24h."),
        _check("recent_traces", recent_traces.exists(), f"{recent_traces.count()} trace sample(s) recorded in the last 24h."),
        _check("active_slos", active_slos.exists(), f"{active_slos.count()} active SLO(s) configured."),
        _check("recent_slo_snapshots", recent_slo_snapshots.exists(), f"{recent_slo_snapshots.count()} SLO snapshot(s) created in the last 7d."),
        _check("active_alert_rules", active_alert_rules.exists(), f"{active_alert_rules.count()} active alert rule(s) configured."),
        _check("open_critical_alerts", critical_open_alerts.count() == 0, f"{critical_open_alerts.count()} open critical alert(s).", severity="critical"),
    ]

    critical = [c for c in checks if not c["ok"] and c["severity"] == "critical"]
    warnings = [c for c in checks if not c["ok"] and c["severity"] == "warning"]
    status = "ready" if not critical and not warnings else "degraded" if not critical else "action_required"

    return {
        "status": status,
        "checks": checks,
        "counts": {
            "events_24h": recent_events.count(),
            "error_events_24h": recent_events.filter(severity=ObservabilitySeverity.ERROR).count(),
            "critical_events_24h": recent_events.filter(severity=ObservabilitySeverity.CRITICAL).count(),
            "metrics_24h": recent_metrics.count(),
            "traces_24h": recent_traces.count(),
            "avg_trace_duration_ms_24h": avg_duration,
            "active_slos": active_slos.count(),
            "recent_slo_snapshots_7d": recent_slo_snapshots.count(),
            "active_alert_rules": active_alert_rules.count(),
            "open_alerts": open_alerts.count(),
            "open_critical_alerts": critical_open_alerts.count(),
        },
        "generated_at": now.isoformat(),
    }
