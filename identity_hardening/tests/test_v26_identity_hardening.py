import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import User
from identity_hardening.models import PasskeyCredential, StepUpSession, TrustedDevice


@pytest.mark.django_db
def test_passkey_registration_metadata_flow():
    user = User.objects.create_user(email="passkey@example.com", password="StrongPassw0rd!")
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post("/api/v1/identity/passkeys/register/begin/", {"rp_id": "example.com", "origin": "https://auth.example.com"}, format="json")
    assert response.status_code == 201
    assert response.data["challenge"]

    complete = client.post(
        "/api/v1/identity/passkeys/register/complete/",
        {"label": "MacBook passkey", "raw_credential_id": "credential-123", "public_key_jwk": {"kty": "EC"}, "platform": "web"},
        format="json",
    )
    assert complete.status_code == 201
    assert PasskeyCredential.objects.filter(user=user, label="MacBook passkey", status="active").exists()


@pytest.mark.django_db
def test_trusted_device_create_and_revoke():
    user = User.objects.create_user(email="device@example.com", password="StrongPassw0rd!")
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post("/api/v1/identity/trusted-devices/", {"raw_device_id": "device-123", "name": "Windows laptop", "platform": "windows"}, format="json")
    assert response.status_code == 201
    device_id = response.data["id"]
    assert TrustedDevice.objects.filter(user=user, platform="windows", status="active").exists()

    revoke = client.post(f"/api/v1/identity/trusted-devices/{device_id}/revoke/")
    assert revoke.status_code == 200
    assert revoke.data["status"] == "revoked"


@pytest.mark.django_db
def test_step_up_satisfy_and_check():
    user = User.objects.create_user(email="stepup@example.com", password="StrongPassw0rd!")
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post("/api/v1/identity/step-up-sessions/satisfy/", {"trigger": "billing_change", "method": "passkey"}, format="json")
    assert response.status_code == 201
    assert StepUpSession.objects.filter(user=user, trigger="billing_change").exists()

    check = client.post("/api/v1/identity/step-up-sessions/check/", {"trigger": "billing_change", "required_method": "passkey"}, format="json")
    assert check.status_code == 200
    assert check.data["satisfied"] is True
