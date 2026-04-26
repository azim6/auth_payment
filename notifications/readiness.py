from __future__ import annotations

from django.utils import timezone

from .models import (
    DevicePushToken,
    NotificationDelivery,
    NotificationEvent,
    NotificationPreference,
    NotificationProvider,
    NotificationTemplate,
)

REQUIRED_TOPICS = ["security", "billing", "account", "compliance"]
REQUIRED_CHANNELS = ["email"]


def _check(name: str, ok: bool, detail: str, severity: str = "warning") -> dict:
    return {"name": name, "ok": bool(ok), "severity": "ok" if ok else severity, "detail": detail}


def build_notification_readiness_report() -> dict:
    """Return an operator-facing readiness report for notification delivery.

    The report is intentionally read-only and safe for staff dashboards. It does
    not expose recipient addresses or raw push tokens; all sensitive values stay
    hashed in the underlying models.
    """
    now = timezone.now()
    providers_active = NotificationProvider.objects.filter(status=NotificationProvider.Status.ACTIVE).count()
    email_providers = NotificationProvider.objects.filter(channel="email", status=NotificationProvider.Status.ACTIVE).count()
    active_templates = NotificationTemplate.objects.filter(is_active=True).count()
    missing_required_templates = []
    for topic in REQUIRED_TOPICS:
        for channel in REQUIRED_CHANNELS:
            exists = NotificationTemplate.objects.filter(key__icontains=topic, channel=channel, is_active=True).exists()
            if not exists:
                missing_required_templates.append(f"{topic}:{channel}")

    due_pending = NotificationDelivery.objects.filter(status=NotificationDelivery.Status.PENDING, next_attempt_at__lte=now).count()
    failed = NotificationDelivery.objects.filter(status=NotificationDelivery.Status.FAILED).count()
    dead = NotificationDelivery.objects.filter(status=NotificationDelivery.Status.DEAD).count()
    queued_events = NotificationEvent.objects.filter(status__in=[NotificationEvent.Status.RECEIVED, NotificationEvent.Status.QUEUED], scheduled_for__lte=now).count()
    active_push_tokens = DevicePushToken.objects.filter(is_active=True).count()
    preference_count = NotificationPreference.objects.count()

    checks = [
        _check("active_provider", providers_active > 0, f"{providers_active} active provider(s) configured."),
        _check("active_email_provider", email_providers > 0, f"{email_providers} active email provider(s) configured."),
        _check("active_templates", active_templates > 0, f"{active_templates} active template(s) configured."),
        _check("required_templates", not missing_required_templates, f"Missing required templates: {', '.join(missing_required_templates) or 'none'}."),
        _check("due_pending_deliveries", due_pending == 0, f"{due_pending} pending delivery/deliveries are due now.", severity="warning"),
        _check("failed_deliveries", failed == 0, f"{failed} delivery/deliveries are waiting for retry.", severity="warning"),
        _check("dead_letter_deliveries", dead == 0, f"{dead} dead-letter delivery/deliveries need operator review.", severity="critical"),
        _check("queued_events", queued_events == 0, f"{queued_events} queued/received event(s) are ready for dispatch.", severity="warning"),
    ]

    critical = [c for c in checks if not c["ok"] and c["severity"] == "critical"]
    warnings = [c for c in checks if not c["ok"] and c["severity"] == "warning"]
    status = "ready" if not critical and not warnings else "degraded" if not critical else "action_required"

    return {
        "status": status,
        "checks": checks,
        "counts": {
            "active_providers": providers_active,
            "active_email_providers": email_providers,
            "active_templates": active_templates,
            "preferences": preference_count,
            "active_push_tokens": active_push_tokens,
            "queued_events_due": queued_events,
            "pending_deliveries_due": due_pending,
            "failed_deliveries": failed,
            "dead_letter_deliveries": dead,
        },
        "generated_at": now.isoformat(),
    }
