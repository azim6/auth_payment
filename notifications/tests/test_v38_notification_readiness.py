from django.test import TestCase

from notifications.models import NotificationProvider, NotificationTemplate
from notifications.readiness import build_notification_readiness_report


class NotificationReadinessTests(TestCase):
    def test_report_detects_missing_provider_and_templates(self):
        report = build_notification_readiness_report()
        self.assertIn(report["status"], {"degraded", "action_required"})
        names = {check["name"] for check in report["checks"]}
        self.assertIn("active_provider", names)
        self.assertIn("required_templates", names)

    def test_report_passes_provider_and_required_templates(self):
        NotificationProvider.objects.create(name="Local Email", channel="email", provider_code="local")
        for key in ["security-alert", "billing-receipt", "account-notice", "compliance-notice"]:
            NotificationTemplate.objects.create(key=key, channel="email", subject_template=key, body_template="Hello")
        report = build_notification_readiness_report()
        self.assertEqual(report["counts"]["active_email_providers"], 1)
        self.assertTrue(any(check["name"] == "required_templates" and check["ok"] for check in report["checks"]))
