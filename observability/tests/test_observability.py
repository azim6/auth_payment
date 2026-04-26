from django.test import TestCase

from observability.models import AlertRule, ApplicationEvent, MetricSnapshot, ObservabilitySeverity, ServiceLevelObjective
from observability.services import build_observability_summary, calculate_slo_snapshot, evaluate_alert_rule


class ObservabilityTests(TestCase):
    def test_records_summary_and_slo_snapshot(self):
        ApplicationEvent.objects.create(event_type="auth.login.success", severity=ObservabilitySeverity.INFO)
        ApplicationEvent.objects.create(event_type="auth.login.failed", severity=ObservabilitySeverity.ERROR)
        slo = ServiceLevelObjective.objects.create(name="auth-api-success", source_app="auth-platform", target_percentage="99.000")
        snapshot = calculate_slo_snapshot(slo)
        summary = build_observability_summary()
        self.assertEqual(summary["events_24h"], 2)
        self.assertEqual(snapshot.total_events, 2)
        self.assertEqual(snapshot.good_events, 1)

    def test_alert_rule_triggers_from_metric(self):
        rule = AlertRule.objects.create(name="high-login-errors", metric_name="auth.login.error_rate", comparator=AlertRule.Comparator.GTE, threshold="5")
        MetricSnapshot.objects.create(name="auth.login.error_rate", value="10", kind=MetricSnapshot.Kind.GAUGE)
        incident = evaluate_alert_rule(rule)
        self.assertIsNotNone(incident)
        self.assertEqual(incident.rule, rule)
