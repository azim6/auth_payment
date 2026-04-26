from unittest.mock import patch

import pytest
from django.urls import reverse
from django.utils import timezone

from accounts.models import Organization, OrganizationMembership, User
from billing.models import BillingCustomer, CheckoutSession, Plan, Price, Project, Subscription
from billing.webhooks import process_stripe_event


@pytest.mark.django_db
def test_owner_can_create_checkout_session(api_client):
    user = User.objects.create_user(email="owner@example.com", password="Password123!")
    org = Organization.objects.create(name="Acme", slug="acme", owner=user)
    OrganizationMembership.objects.create(organization=org, user=user, role=OrganizationMembership.Role.OWNER)
    project = Project.objects.create(code="store", name="Store")
    plan = Plan.objects.create(project=project, code="store-pro", name="Store Pro")
    price = Price.objects.create(plan=plan, code="store-pro-month", amount_cents=2900, provider_price_id="price_123")
    api_client.force_authenticate(user=user)

    provider_session = type("ProviderSession", (), {"provider_session_id": "cs_test_123", "url": "https://checkout.example/session", "expires_at": timezone.now(), "raw": {"id": "cs_test_123"}})()
    with patch("billing.views.get_billing_provider") as get_provider:
        get_provider.return_value.create_checkout_session.return_value = provider_session
        response = api_client.post(reverse("billing-create-checkout-session"), {
            "organization_slug": "acme",
            "price_code": "store-pro-month",
            "success_url": "https://store.example.com/billing/success",
            "cancel_url": "https://store.example.com/billing/cancel",
        }, format="json")

    assert response.status_code == 201
    assert response.data["provider_session_id"] == "cs_test_123"
    assert CheckoutSession.objects.filter(customer__organization=org, price=price).exists()


@pytest.mark.django_db
def test_stripe_subscription_webhook_upserts_subscription():
    customer = BillingCustomer.objects.create(billing_email="billing@example.com", provider="stripe", provider_customer_id="cus_123")
    project = Project.objects.create(code="api", name="API")
    plan = Plan.objects.create(project=project, code="api-pro", name="API Pro")
    Price.objects.create(plan=plan, code="api-pro-month", amount_cents=4900, provider_price_id="price_abc")

    event = {
        "id": "evt_123",
        "type": "customer.subscription.updated",
        "data": {
            "object": {
                "id": "sub_123",
                "customer": "cus_123",
                "status": "active",
                "current_period_start": 1710000000,
                "current_period_end": 1712600000,
                "cancel_at_period_end": False,
                "items": {"data": [{"quantity": 1, "price": {"id": "price_abc"}}]},
            }
        },
    }

    webhook = process_stripe_event(event, signature_valid=True)

    assert webhook.status == "processed"
    subscription = Subscription.objects.get(provider="stripe", provider_subscription_id="sub_123")
    assert subscription.customer == customer
    assert subscription.plan == plan
    assert subscription.status == Subscription.Status.ACTIVE
