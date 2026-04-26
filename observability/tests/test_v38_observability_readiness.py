from django.test import TestCase

from observability.models import AlertRule, ApplicationEvent, MetricSnapshot, ObservabilitySeverity, ServiceLevelObjective, TraceSample
from observability.readiness import build_observability_readiness_report
from observability.services import calculate_slo_snapshot


class ObservabilityReadinessTests(TestCase):
    def test_report_surfaces_missing_telemetry(self):
        report = build_observability_readiness_report()
        names = {check["name"] for check in report["checks"]}
        self.assertIn("recent_application_events", names)
        self.assertIn("active_slos", names)
        self.assertIn(report["status"], {"degraded", "action_required"})

    def test_report_passes_core_observability_setup(self):
        ApplicationEvent.objects.create(event_type="auth.login.success", severity=ObservabilitySeverity.INFO)
        MetricSnapshot.objects.create(name="auth.login.error_rate", value="0", kind=MetricSnapshot.Kind.GAUGE)
        TraceSample.objects.create(trace_id="trace_1", method="GET", path="/api/v1/auth/session/status/", status_code=200, duration_ms=12)
        slo = ServiceLevelObjective.objects.create(name="auth-login", source_app="auth-platform")
        calculate_slo_snapshot(slo)
        AlertRule.objects.create(name="auth-errors", metric_name="auth.login.error_rate", threshold="5")
        report = build_observability_readiness_report()
        self.assertEqual(report["counts"]["active_slos"], 1)
        self.assertTrue(any(check["name"] == "active_alert_rules" and check["ok"] for check in report["checks"]))
