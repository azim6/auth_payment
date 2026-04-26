import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from accounts.models import AuditLog, ServiceCredential


@pytest.fixture
def admin_user(db):
    return get_user_model().objects.create_superuser(
        email="admin@example.com",
        username="admin",
        password="StrongPassword123!",
    )


@pytest.mark.django_db
def test_admin_can_create_service_credential(client, admin_user):
    client.force_login(admin_user)
    response = client.post(
        reverse("service-credentials"),
        {"name": "blog-service", "scopes": "users:read tokens:introspect"},
        content_type="application/json",
    )

    assert response.status_code == 201
    assert response.json()["raw_key"].startswith("svc_")
    assert ServiceCredential.objects.filter(name="blog-service").exists()
    assert AuditLog.objects.filter(action="service_credential.created").exists()


@pytest.mark.django_db
def test_service_key_can_be_exchanged_for_short_lived_token(client, admin_user):
    client.force_login(admin_user)
    create_response = client.post(
        reverse("service-credentials"),
        {"name": "worker-service", "scopes": "users:read"},
        content_type="application/json",
    )
    raw_key = create_response.json()["raw_key"]
    client.logout()

    response = client.post(
        reverse("service-token"),
        {"grant_type": "client_credentials", "service_key": raw_key, "scope": "users:read"},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert "access_token" in response.json()
    assert AuditLog.objects.filter(action="service_token.issued").exists()


@pytest.mark.django_db
def test_non_admin_cannot_read_audit_logs(client):
    response = client.get(reverse("audit-logs"))
    assert response.status_code in {302, 401, 403}
