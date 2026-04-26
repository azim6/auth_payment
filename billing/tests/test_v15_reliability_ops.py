import pytest
from django.utils import timezone

from billing.models import BillingWebhookEvent, EntitlementChangeLog
from billing.services import (
    create_webhook_replay_request,
    dispatch_due_outbox_events,
    enqueue_billing_outbox_event,
    recalculate_entitlement_snapshot_with_log,
    update_provider_sync_failure,
    update_provider_sync_success,
)


@pytest.mark.django_db
def test_outbox_idempotency_and_dispatch():
    event = enqueue_billing_outbox_event(
        event_type="billing.subscription.changed",
        aggregate_type="subscription",
        aggregate_id="sub_123",
        payload={"subscription": "sub_123"},
        idempotency_key="sub_123:v1",
    )
    same = enqueue_billing_outbox_event(
        event_type="billing.subscription.changed",
        aggregate_type="subscription",
        aggregate_id="sub_123",
        payload={"subscription": "sub_123"},
        idempotency_key="sub_123:v1",
    )
    assert same.id == event.id
    result = dispatch_due_outbox_events(limit=10)
    event.refresh_from_db()
    assert result["dispatched"] == 1
    assert event.status == event.Status.DISPATCHED
    assert event.dispatched_at is not None


@pytest.mark.django_db
def test_provider_sync_health_records_success_and_failure():
    state = update_provider_sync_success(provider="stripe", resource_type="subscriptions", cursor="cur_1", lag_seconds=3)
    assert state.status == state.Status.HEALTHY
    assert state.cursor == "cur_1"
    failed = update_provider_sync_failure(provider="stripe", resource_type="subscriptions", error="timeout")
    assert failed.error_count == 1
    assert failed.status == failed.Status.DEGRADED


@pytest.mark.django_db
def test_webhook_replay_request_records_failure_for_unknown_provider(admin_user):
    webhook = BillingWebhookEvent.objects.create(
        provider="unknown",
        event_id="evt_1",
        event_type="test.event",
        payload={"id": "evt_1", "type": "test.event"},
        signature_valid=True,
        status=BillingWebhookEvent.Status.FAILED,
    )
    replay = create_webhook_replay_request(webhook_event=webhook, actor=admin_user, process_now=True)
    assert replay.status == replay.Status.FAILED
    assert "No replay handler" in replay.error


@pytest.mark.django_db
def test_entitlement_snapshot_recalculation_writes_change_log(billing_customer, admin_user):
    snapshot = recalculate_entitlement_snapshot_with_log(customer=billing_customer, reason="test", actor=admin_user)
    log = EntitlementChangeLog.objects.get(customer=billing_customer)
    assert log.snapshot == snapshot
    assert log.reason == "test"
    assert log.changed_by == admin_user
