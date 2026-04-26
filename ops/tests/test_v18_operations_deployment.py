from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from ops.models import MaintenanceWindow, ReleaseRecord, StatusIncident


class OperationsDeploymentTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_superuser(email="ops@example.com", password="StrongPassword123!")

    def test_public_liveness_is_available(self):
        response = self.client.get(reverse("ops-live"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["alive"], True)

    def test_staff_can_create_maintenance_window(self):
        self.client.force_authenticate(self.admin)
        now = timezone.now()
        response = self.client.post(reverse("maintenance-window-list"), {
            "title": "Database migration",
            "status": MaintenanceWindow.Status.SCHEDULED,
            "starts_at": now.isoformat(),
            "ends_at": (now + timezone.timedelta(hours=1)).isoformat(),
            "affected_services": ["auth", "billing"],
            "customer_message": "Planned maintenance.",
        }, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(MaintenanceWindow.objects.count(), 1)

    def test_public_status_includes_active_incidents(self):
        StatusIncident.objects.create(title="Stripe degraded", impact=StatusIncident.Impact.MINOR, public_message="Payments are delayed.")
        response = self.client.get(reverse("ops-public-status"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "degraded")

    def test_staff_can_mark_release_deployed(self):
        self.client.force_authenticate(self.admin)
        release = ReleaseRecord.objects.create(version="18.0.0", git_sha="abc123", image_tag="auth:18")
        response = self.client.post(reverse("release-record-deploy", args=[release.id]), {"mark_deployed": True}, format="json")
        self.assertEqual(response.status_code, 200)
        release.refresh_from_db()
        self.assertEqual(release.status, ReleaseRecord.Status.RELEASED)
        self.assertEqual(release.deployed_by, self.admin)
