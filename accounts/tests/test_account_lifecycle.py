import pytest
from django.core import mail
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import AccountToken, User


@pytest.mark.django_db(transaction=True)
def test_register_sends_verification_email_and_confirm_marks_verified(settings):
    client = APIClient()
    response = client.post(
        reverse("auth-register"),
        {
            "email": "verify@example.com",
            "username": "verifyuser",
            "display_name": "Verify User",
            "password": "VeryStrongPassword123!",
            "password_confirm": "VeryStrongPassword123!",
        },
        format="json",
    )

    assert response.status_code == 201
    assert len(mail.outbox) == 1
    token = mail.outbox[0].body.split("token=")[1].split()[0]

    confirm = client.post(reverse("email-verify-confirm"), {"token": token}, format="json")
    assert confirm.status_code == 200

    user = User.objects.get(email="verify@example.com")
    assert user.email_verified is True
    assert AccountToken.objects.get(user=user, purpose=AccountToken.Purpose.EMAIL_VERIFICATION).used_at is not None


@pytest.mark.django_db(transaction=True)
def test_password_reset_changes_password_and_rejects_token_reuse(settings):
    user = User.objects.create_user(
        email="reset@example.com",
        username="resetuser",
        password="OldStrongPassword123!",
    )
    client = APIClient()

    response = client.post(reverse("password-reset-request"), {"email": user.email}, format="json")
    assert response.status_code == 202
    assert len(mail.outbox) == 1
    token = mail.outbox[0].body.split("token=")[1].split()[0]

    confirm = client.post(
        reverse("password-reset-confirm"),
        {
            "token": token,
            "new_password": "NewStrongPassword123!",
            "new_password_confirm": "NewStrongPassword123!",
        },
        format="json",
    )
    assert confirm.status_code == 200

    login = client.post(
        reverse("token-obtain-pair"),
        {"email": user.email, "password": "NewStrongPassword123!"},
        format="json",
    )
    assert login.status_code == 200

    reuse = client.post(
        reverse("password-reset-confirm"),
        {
            "token": token,
            "new_password": "AnotherStrongPassword123!",
            "new_password_confirm": "AnotherStrongPassword123!",
        },
        format="json",
    )
    assert reuse.status_code == 400
