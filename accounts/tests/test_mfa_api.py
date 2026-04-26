import pyotp
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.mfa import unsign_secret
from accounts.models import MfaDevice, RecoveryCode, User


def create_user():
    return User.objects.create_user(
        email="mfa@example.com",
        username="mfauser",
        password="VeryStrongPassword123!",
        email_verified=True,
    )


def test_user_can_enable_totp_mfa(db):
    user = create_user()
    client = APIClient()
    assert client.login(email="mfa@example.com", password="VeryStrongPassword123!")

    start = client.post(reverse("mfa-setup-start"), {"name": "Phone"}, format="json")
    assert start.status_code == 201
    assert "provisioning_uri" in start.data

    device = MfaDevice.objects.get(user=user)
    secret = unsign_secret(device.secret)
    code = pyotp.TOTP(secret).now()

    confirm = client.post(reverse("mfa-setup-confirm"), {"otp": code}, format="json")
    assert confirm.status_code == 200
    assert len(confirm.data["recovery_codes"]) == 10
    assert MfaDevice.objects.get(user=user).is_confirmed
    assert RecoveryCode.objects.filter(user=user, used_at__isnull=True).count() == 10


def test_token_login_requires_mfa_after_enabled(db):
    user = create_user()
    device = MfaDevice.objects.create(
        user=user,
        secret="placeholder",
        confirmed_at=timezone.now(),
    )
    from accounts.mfa import generate_totp_secret, sign_secret
    secret = generate_totp_secret()
    device.secret = sign_secret(secret)
    device.save(update_fields=["secret"])

    client = APIClient()
    without_mfa = client.post(reverse("token-obtain-pair"), {
        "email": "mfa@example.com",
        "password": "VeryStrongPassword123!",
    }, format="json")
    assert without_mfa.status_code == 400

    with_mfa = client.post(reverse("token-obtain-pair"), {
        "email": "mfa@example.com",
        "password": "VeryStrongPassword123!",
        "otp": pyotp.TOTP(secret).now(),
    }, format="json")
    assert with_mfa.status_code == 200
    assert "access" in with_mfa.data
    assert "refresh" in with_mfa.data
