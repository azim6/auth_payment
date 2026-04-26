import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from customer_portal.models import PortalSupportRequest


@pytest.mark.django_db
def test_customer_portal_readiness_requires_staff(django_user_model):
    user = django_user_model.objects.create_user(email="user@example.com", password="x")
    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get(reverse("portal-readiness"))
    assert response.status_code == 403


@pytest.mark.django_db
def test_customer_portal_readiness_for_staff(django_user_model):
    user = django_user_model.objects.create_user(email="staff@example.com", password="x", is_staff=True)
    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get(reverse("portal-readiness"))
    assert response.status_code == 200
    assert response.data["component"] == "customer_portal"
    assert "checks" in response.data


@pytest.mark.django_db
def test_support_request_escalates_to_operator_task(django_user_model):
    user = django_user_model.objects.create_user(email="customer@example.com", password="x")
    request = PortalSupportRequest.objects.create(
        user=user,
        category=PortalSupportRequest.Category.ACCOUNT,
        subject="Need help",
        message="Please help",
    )
    client = APIClient()
    client.force_authenticate(user=user)
    response = client.post(reverse("portal-support-requests-escalate", args=[request.id]))
    assert response.status_code == 200
    request.refresh_from_db()
    assert request.operator_task_id is not None
    assert request.status == PortalSupportRequest.Status.WAITING_ON_SUPPORT
