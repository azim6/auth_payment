from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import User
from ops.services import build_production_boot_validation_payload


class ProductionBootValidationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_superuser(email="ops-v40@example.com", password="StrongPassword123!")

    @override_settings(
        DEBUG=False,
        SECRET_KEY="x" * 64,
        ALLOWED_HOSTS=["auth.example.com"],
        SESSION_COOKIE_SECURE=True,
        CSRF_COOKIE_SECURE=True,
        CSRF_TRUSTED_ORIGINS=["https://admin.example.com"],
        CORS_ALLOWED_ORIGINS=["https://admin.example.com"],
        PRODUCTION_BOOT_EXPECTED_HOSTS=["auth.example.com"],
        PRODUCTION_BOOT_EXPECTED_ORIGINS=["https://admin.example.com"],
    )
    def test_validation_payload_has_required_shape(self):
        payload = build_production_boot_validation_payload()
        self.assertIn("ready", payload)
        self.assertIn("checks", payload)
        self.assertIn("admin_system_compatible", payload)
        self.assertTrue(any(check["key"] == "database_connectivity" for check in payload["checks"]))

    def test_staff_can_call_production_validation_endpoint(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(reverse("ops-production-validation"))
        self.assertIn(response.status_code, [200, 503])
        self.assertIn("checks", response.data)
