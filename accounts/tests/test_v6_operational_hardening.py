import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import AuthSessionDevice, RefreshTokenFamily, ServiceCredential, User


@pytest.mark.django_db
def test_session_login_records_device():
    user = User.objects.create_user(email="user@example.com", username="userone", password="testpass12345")
    client = APIClient()
    response = client.post(
        reverse("session-login"),
        {"email": user.email, "password": "testpass12345"},
        HTTP_USER_AGENT="Mozilla/5.0 Windows",
    )

    assert response.status_code == 200
    assert AuthSessionDevice.objects.filter(user=user, label="Windows device").exists()


@pytest.mark.django_db
def test_token_login_records_refresh_family():
    user = User.objects.create_user(email="user@example.com", username="userone", password="testpass12345")
    client = APIClient()
    response = client.post(
        reverse("token-obtain-pair"),
        {"email": user.email, "password": "testpass12345"},
        HTTP_USER_AGENT="Android App",
    )

    assert response.status_code == 200
    assert RefreshTokenFamily.objects.filter(user=user, user_agent="Android App").exists()


@pytest.mark.django_db
def test_user_can_revoke_refresh_families():
    user = User.objects.create_user(email="user@example.com", username="userone", password="testpass12345")
    RefreshTokenFamily.objects.create(
        user=user,
        jti="jti-test",
        expires_at="2099-01-01T00:00:00Z",
    )
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(reverse("auth-refresh-token-revoke-all"))

    assert response.status_code == 200
    assert response.data["revoked"] == 1
    assert RefreshTokenFamily.objects.filter(user=user, revoked_at__isnull=False).count() == 1


@pytest.mark.django_db
def test_admin_can_deactivate_service_credential():
    admin_user = User.objects.create_superuser(email="admin@example.com", username="admin", password="testpass12345")
    user = User.objects.create_user(email="user@example.com", username="userone", password="testpass12345")
    credential = ServiceCredential.objects.create(
        owner=user,
        name="blog-service",
        key_prefix="svc_test",
        key_hash="hashed",
        scopes="users:read",
    )
    client = APIClient()
    client.force_authenticate(user=admin_user)

    response = client.post(reverse("service-credential-deactivate", kwargs={"credential_id": credential.id}))

    assert response.status_code == 204
    credential.refresh_from_db()
    assert credential.is_active is False
