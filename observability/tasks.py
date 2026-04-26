from __future__ import annotations

from celery import shared_task

from .models import AlertRule, ServiceLevelObjective
from .services import calculate_slo_snapshot, evaluate_alert_rule


@shared_task
def calculate_active_slo_snapshots() -> int:
    count = 0
    for slo in ServiceLevelObjective.objects.filter(is_active=True):
        calculate_slo_snapshot(slo)
        count += 1
    return count


@shared_task
def evaluate_active_alert_rules() -> int:
    triggered = 0
    for rule in AlertRule.objects.filter(status=AlertRule.Status.ACTIVE):
        if evaluate_alert_rule(rule):
            triggered += 1
    return triggered
