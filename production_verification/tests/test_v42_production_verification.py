from django.test import TestCase

from production_verification.checks import feature_flag_inventory, run_production_verification


class ProductionVerificationTests(TestCase):
    def test_verification_payload_has_expected_shape(self):
        result = run_production_verification()
        assert result["status"] in {"pass", "warn", "fail"}
        assert "summary" in result
        assert "checks" in result

    def test_feature_inventory_marks_core_apps(self):
        rows = feature_flag_inventory()
        labels = {row["app_label"] for row in rows}
        assert "accounts" in labels
        assert "billing" in labels
        assert "admin_integration" in labels
