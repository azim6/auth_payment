from django.core.management.base import BaseCommand

from observability.models import AlertRule, ServiceLevelObjective
from observability.services import build_observability_summary, calculate_slo_snapshot, evaluate_alert_rule, record_event, record_metric


class Command(BaseCommand):
    help = "Create an observability heartbeat metric, calculate SLO snapshots, and evaluate alert rules."

    def handle(self, *args, **options):
        summary = build_observability_summary()
        record_event(event_type="observability.snapshot.created", message="Observability snapshot command completed", payload=summary)
        record_metric(name="observability.open_alerts", value=summary["open_alerts"], kind="gauge", unit="alerts")
        slo_count = 0
        for slo in ServiceLevelObjective.objects.filter(is_active=True):
            calculate_slo_snapshot(slo)
            slo_count += 1
        alert_count = 0
        for rule in AlertRule.objects.filter(status=AlertRule.Status.ACTIVE):
            if evaluate_alert_rule(rule):
                alert_count += 1
        self.stdout.write(self.style.SUCCESS(f"observability snapshot complete: {slo_count} SLOs, {alert_count} alerts triggered"))
