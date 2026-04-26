import pytest
from django.utils import timezone

from billing.models import BillingCustomer, BillingWebhookEvent, CheckoutSession, Price, Project, Plan, Subscription
from billing.webhooks import process_stripe_event


@pytest.mark.django_db
def test_stripe_checkout_completed_marks_session_and_processes_once(organization):
    customer = BillingCustomer.objects.create(organization=organization, provider="stripe", provider_customer_id="cus_123")
    project = Project.objects.create(code="store", name="Store")
    plan = Plan.objects.create(project=project, code="store-pro", name="Store Pro")
    price = Price.objects.create(plan=plan, code="store-pro-month", amount_cents=1000, provider_price_id="price_123")
    checkout = CheckoutSession.objects.create(customer=customer, plan=plan, price=price, provider="stripe", provider_session_id="cs_123")
    event = {"id": "evt_123", "type": "checkout.session.completed", "data": {"object": {"id": "cs_123", "customer": "cus_123"}}}

    processed = process_stripe_event(event)
    processed_again = process_stripe_event(event)

    checkout.refresh_from_db()
    assert checkout.status == CheckoutSession.Status.COMPLETED
    assert processed.id == processed_again.id
    assert BillingWebhookEvent.objects.filter(event_id="evt_123").count() == 1


@pytest.mark.django_db
def test_stripe_subscription_update_creates_subscription_and_snapshot(organization):
    customer = BillingCustomer.objects.create(organization=organization, provider="stripe", provider_customer_id="cus_sub")
    project = Project.objects.create(code="blog", name="Blog")
    plan = Plan.objects.create(project=project, code="blog-pro", name="Blog Pro")
    Price.objects.create(plan=plan, code="blog-pro-month", amount_cents=1200, provider_price_id="price_blog")
    event = {
        "id": "evt_sub",
        "type": "customer.subscription.updated",
        "data": {"object": {
            "id": "sub_123",
            "customer": "cus_sub",
            "status": "active",
            "current_period_start": int(timezone.now().timestamp()),
            "current_period_end": int((timezone.now() + timezone.timedelta(days=30)).timestamp()),
            "items": {"data": [{"quantity": 3, "price": {"id": "price_blog"}}]},
        }},
    }

    process_stripe_event(event)

    subscription = Subscription.objects.get(provider_subscription_id="sub_123")
    assert subscription.status == Subscription.Status.ACTIVE
    assert subscription.seat_limit == 3
    assert customer.entitlement_snapshots.exists()
