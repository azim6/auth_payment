import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import User


@pytest.mark.django_db
def test_register_user():
    client = APIClient()
    response = client.post(
        reverse("auth-register"),
        {
            "email": "user@example.com",
            "username": "userone",
            "display_name": "User One",
            "password": "VeryStrongPassword123!",
            "password_confirm": "VeryStrongPassword123!",
        },
        format="json",
    )

    assert response.status_code == 201
    assert User.objects.filter(email="user@example.com").exists()


@pytest.mark.django_db
def test_jwt_login_and_me():
    user = User.objects.create_user(
        email="user@example.com",
        username="userone",
        password="VeryStrongPassword123!",
        display_name="User One",
    )
    client = APIClient()

    token_response = client.post(
        reverse("token-obtain-pair"),
        {"email": "user@example.com", "password": "VeryStrongPassword123!"},
        format="json",
    )
    assert token_response.status_code == 200
    access = token_response.data["access"]

    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    me_response = client.get(reverse("users-me"))

    assert me_response.status_code == 200
    assert me_response.data["id"] == str(user.id)
    assert me_response.data["email"] == "user@example.com"


@pytest.mark.django_db
def test_public_profile():
    user = User.objects.create_user(
        email="user@example.com",
        username="userone",
        password="VeryStrongPassword123!",
        display_name="User One",
    )
    client = APIClient()

    response = client.get(reverse("users-public-profile", kwargs={"user_id": user.id}))

    assert response.status_code == 200
    assert response.data["username"] == "userone"
    assert "email" not in response.data
