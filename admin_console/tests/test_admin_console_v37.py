import pytest
from django.urls import reverse
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_admin_console_readiness_requires_staff(django_user_model):
    user = django_user_model.objects.create_user(email="user@example.com", password="x")
    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get(reverse("admin-console-readiness"))
    assert response.status_code == 403


@pytest.mark.django_db
def test_admin_console_readiness_for_staff(django_user_model):
    user = django_user_model.objects.create_user(email="staff@example.com", password="x", is_staff=True)
    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get(reverse("admin-console-readiness"))
    assert response.status_code == 200
    assert response.data["component"] == "admin_console"
    assert "checks" in response.data
