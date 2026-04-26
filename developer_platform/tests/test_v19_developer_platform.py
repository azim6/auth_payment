import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from accounts.models import Organization, OrganizationMembership
from billing.models import Project
from developer_platform.models import DeveloperApplication, WebhookSubscription

pytestmark = pytest.mark.django_db


def make_owner():
    user = get_user_model().objects.create_user(email="owner@example.com", password="StrongPass12345!")
    org = Organization.objects.create(name="Acme", slug="acme", owner=user)
    OrganizationMembership.objects.create(organization=org, user=user, role=OrganizationMembership.Role.OWNER)
    return user, org


def test_owner_can_create_web_application_and_receives_secret_once():
    user, org = make_owner()
    project = Project.objects.create(code="store", name="Store")
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post("/api/v1/platform/applications/", {
        "organization": str(org.id),
        "project": str(project.id),
        "name": "Store Web",
        "slug": "store-web",
        "app_type": "web",
        "environment": "production",
        "redirect_uris": ["https://store.example.com/auth/callback"],
        "allowed_origins": ["https://store.example.com"],
        "allowed_scopes": "openid profile billing.read",
    }, format="json")

    assert response.status_code == 201
    assert response.data["client_id"].startswith("app_")
    assert response.data["raw_client_secret"].startswith("appsec_")
    app = DeveloperApplication.objects.get(id=response.data["id"])
    assert app.check_client_secret(response.data["raw_client_secret"])


def test_webhook_secret_is_hashed_and_rotatable():
    user, org = make_owner()
    app = DeveloperApplication.objects.create(
        organization=org,
        name="Blog Android",
        slug="blog-android",
        app_type="android",
        client_id=DeveloperApplication.generate_client_id(),
    )
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post("/api/v1/platform/webhooks/subscriptions/", {
        "organization": str(org.id),
        "application": str(app.id),
        "name": "Blog webhook",
        "target_url": "https://blog.example.com/webhooks/auth",
        "event_types": ["user.created", "billing.subscription.changed"],
    }, format="json")

    assert response.status_code == 201
    raw_secret = response.data["raw_webhook_secret"]
    subscription = WebhookSubscription.objects.get(id=response.data["id"])
    assert subscription.check_secret(raw_secret)

    rotated = client.post(f"/api/v1/platform/webhooks/subscriptions/{subscription.id}/rotate-secret/")
    assert rotated.status_code == 200
    assert rotated.data["raw_webhook_secret"].startswith("whsec_")
    subscription.refresh_from_db()
    assert subscription.check_secret(rotated.data["raw_webhook_secret"])
