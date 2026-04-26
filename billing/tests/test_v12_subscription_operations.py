import pytest
from django.utils import timezone

from billing.models import SubscriptionChangeRequest, UsageMetric
from billing.services import apply_subscription_change, record_usage, usage_total_for_period


@pytest.mark.django_db
def test_apply_cancel_at_period_end(subscription, admin_user):
    change = SubscriptionChangeRequest.objects.create(
        subscription=subscription,
        action=SubscriptionChangeRequest.Action.CANCEL_AT_PERIOD_END,
        requested_by=admin_user,
        reason="customer requested downgrade at renewal",
    )
    updated = apply_subscription_change(change)
    assert updated.cancel_at_period_end is True
    change.refresh_from_db()
    assert change.status == SubscriptionChangeRequest.Status.APPLIED


@pytest.mark.django_db
def test_usage_record_idempotency(billing_customer, project):
    metric = UsageMetric.objects.create(
        project=project,
        code="api-requests",
        name="API requests",
        unit="request",
        entitlement_key="api.requests.monthly.max",
    )
    first = record_usage(customer=billing_customer, metric=metric, quantity=5, idempotency_key="evt_1")
    second = record_usage(customer=billing_customer, metric=metric, quantity=5, idempotency_key="evt_1")
    assert first.id == second.id


@pytest.mark.django_db
def test_usage_total_for_period(billing_customer, project):
    metric = UsageMetric.objects.create(
        project=project,
        code="blog-posts",
        name="Blog posts",
        unit="post",
        entitlement_key="blog.posts.max",
    )
    now = timezone.now()
    record_usage(customer=billing_customer, metric=metric, quantity=2)
    record_usage(customer=billing_customer, metric=metric, quantity=3)
    assert usage_total_for_period(customer=billing_customer, metric=metric, start=now.replace(day=1, hour=0, minute=0, second=0, microsecond=0), end=timezone.now()) == 5
