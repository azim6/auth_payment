from django.urls import reverse
from rest_framework.test import APIClient

from accounts.auth_completion import build_auth_readiness_report
from accounts.models import AuditLog, User


def test_auth_readiness_report_shape(db, settings):
    settings.AUTH_USER_MODEL = "accounts.User"
    report = build_auth_readiness_report()

    assert report["component"] == "auth_identity"
    assert report["version"] == "35.0.0"
    assert report["overall_status"] in {"pass", "warn", "fail"}
    assert report["totals"]
    assert any(check["key"] == "custom_user_model" for check in report["checks"])
    assert any(check["key"] == "refresh_token_inventory" for check in report["checks"])


def test_auth_readiness_endpoint_requires_staff(db):
    user = User.objects.create_user(email="user@example.com", username="user", password="StrongPass12345!")
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.get(reverse("auth-readiness"))

    assert response.status_code == 403


def test_auth_readiness_endpoint_for_staff_writes_audit(db):
    staff = User.objects.create_user(email="staff@example.com", username="staff", password="StrongPass12345!", is_staff=True)
    client = APIClient()
    client.force_authenticate(user=staff)

    response = client.get(reverse("auth-readiness"))

    assert response.status_code == 200
    assert response.data["component"] == "auth_identity"
    assert AuditLog.objects.filter(actor=staff, action="auth_readiness_checked").exists()
