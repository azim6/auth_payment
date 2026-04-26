from __future__ import annotations

from datetime import datetime, timezone as dt_timezone

from django.db import transaction
from django.utils import timezone

from .models import BillingCustomer, BillingWebhookEvent, CheckoutSession, Invoice, PaymentTransaction, Price, Subscription
from .services import (
    enqueue_billing_outbox_event,
    open_or_update_dunning_case,
    recalculate_entitlement_snapshot_with_log,
    update_provider_sync_failure,
    update_provider_sync_success,
)


@transaction.atomic
def process_stripe_event(event: dict, *, signature_valid: bool = True) -> BillingWebhookEvent:
    """Idempotently process a Stripe webhook and update local billing state.

    v34 closes the main production gap from the earlier scaffold: payment provider
    events now invalidate/rebuild entitlement snapshots and enqueue outbound billing
    events for downstream apps after subscription, invoice, and payment changes.
    """
    event_id = event.get("id", "")
    event_type = event.get("type", "unknown")
    webhook, created = BillingWebhookEvent.objects.get_or_create(
        provider="stripe",
        event_id=event_id,
        defaults={"event_type": event_type, "payload": event, "signature_valid": signature_valid},
    )
    if not created and webhook.status == BillingWebhookEvent.Status.PROCESSED:
        return webhook

    touched_customer = None
    try:
        data_object = event.get("data", {}).get("object", {})
        if event_type == "checkout.session.completed":
            touched_customer = _handle_checkout_completed(data_object)
        elif event_type == "checkout.session.expired":
            touched_customer = _handle_checkout_expired(data_object)
        elif event_type in {"customer.subscription.created", "customer.subscription.updated"}:
            touched_customer = _upsert_subscription_from_stripe(data_object)
        elif event_type == "customer.subscription.deleted":
            touched_customer = _cancel_subscription_from_stripe(data_object)
        elif event_type in {"invoice.paid", "invoice.payment_failed", "invoice.finalized", "invoice.voided", "invoice.marked_uncollectible"}:
            touched_customer = _upsert_invoice_from_stripe(data_object, event_type)
        elif event_type in {"payment_intent.succeeded", "payment_intent.payment_failed", "payment_intent.processing", "payment_intent.requires_action"}:
            touched_customer = _upsert_payment_from_stripe(data_object, event_type)
        elif event_type == "charge.refunded":
            touched_customer = _mark_payment_refunded_from_charge(data_object)
        if touched_customer:
            recalculate_entitlement_snapshot_with_log(
                customer=touched_customer,
                reason=f"stripe_webhook:{event_type}",
                actor=None,
                metadata={"provider_event_id": event_id},
            )
            enqueue_billing_outbox_event(
                event_type="billing.provider_event.processed",
                aggregate_type="billing_customer",
                aggregate_id=str(touched_customer.id),
                payload={"provider": "stripe", "event_id": event_id, "event_type": event_type, "customer_id": str(touched_customer.id)},
                idempotency_key=f"stripe:{event_id}:processed",
            )
        update_provider_sync_success(provider="stripe", resource_type="webhook", cursor=event_id, metadata={"last_event_type": event_type})
        webhook.status = BillingWebhookEvent.Status.PROCESSED
        webhook.error = ""
    except Exception as exc:  # noqa: BLE001 - retained in webhook log for operations
        update_provider_sync_failure(provider="stripe", resource_type="webhook", error=str(exc))
        webhook.status = BillingWebhookEvent.Status.FAILED
        webhook.error = str(exc)
    webhook.event_type = event_type
    webhook.payload = event
    webhook.signature_valid = signature_valid
    webhook.processed_at = timezone.now()
    webhook.save(update_fields=["event_type", "payload", "signature_valid", "status", "processed_at", "error"])
    return webhook


def _customer_from_provider_id(provider_customer_id: str):
    return BillingCustomer.objects.filter(provider="stripe", provider_customer_id=provider_customer_id).first()


def _handle_checkout_completed(obj: dict):
    provider_session_id = obj.get("id", "")
    checkout = CheckoutSession.objects.filter(provider="stripe", provider_session_id=provider_session_id).select_related("customer").first()
    if checkout:
        checkout.status = CheckoutSession.Status.COMPLETED
        checkout.completed_at = timezone.now()
        checkout.save(update_fields=["status", "completed_at", "updated_at"])
        return checkout.customer
    return _customer_from_provider_id(obj.get("customer", ""))


def _handle_checkout_expired(obj: dict):
    provider_session_id = obj.get("id", "")
    checkout = CheckoutSession.objects.filter(provider="stripe", provider_session_id=provider_session_id).select_related("customer").first()
    if checkout:
        checkout.status = CheckoutSession.Status.EXPIRED
        checkout.save(update_fields=["status", "updated_at"])
        return checkout.customer
    return _customer_from_provider_id(obj.get("customer", ""))


def _upsert_subscription_from_stripe(obj: dict):
    customer = _customer_from_provider_id(obj.get("customer", ""))
    if not customer:
        return None
    first_item = (obj.get("items", {}).get("data") or [{}])[0]
    provider_price_id = first_item.get("price", {}).get("id", "")
    price = Price.objects.filter(provider_price_id=provider_price_id).select_related("plan").first()
    if not price:
        return customer
    status_map = {
        "trialing": Subscription.Status.TRIALING,
        "active": Subscription.Status.ACTIVE,
        "past_due": Subscription.Status.PAST_DUE,
        "paused": Subscription.Status.PAUSED,
        "canceled": Subscription.Status.CANCELLED,
        "incomplete_expired": Subscription.Status.EXPIRED,
    }
    Subscription.objects.update_or_create(
        provider="stripe",
        provider_subscription_id=obj.get("id", ""),
        defaults={
            "customer": customer,
            "plan": price.plan,
            "price": price,
            "status": status_map.get(obj.get("status"), Subscription.Status.PAST_DUE),
            "quantity": first_item.get("quantity") or 1,
            "seat_limit": first_item.get("quantity") or 1,
            "trial_ends_at": _ts(obj.get("trial_end")),
            "current_period_start": _ts(obj.get("current_period_start")),
            "current_period_end": _ts(obj.get("current_period_end")),
            "cancel_at_period_end": bool(obj.get("cancel_at_period_end")),
            "cancelled_at": _ts(obj.get("canceled_at")),
        },
    )
    return customer


def _cancel_subscription_from_stripe(obj: dict):
    subscription = Subscription.objects.filter(provider="stripe", provider_subscription_id=obj.get("id", "")).select_related("customer").first()
    if not subscription:
        return _customer_from_provider_id(obj.get("customer", ""))
    subscription.status = Subscription.Status.CANCELLED
    subscription.cancelled_at = _ts(obj.get("canceled_at")) or timezone.now()
    subscription.current_period_end = _ts(obj.get("current_period_end")) or subscription.current_period_end
    subscription.save(update_fields=["status", "cancelled_at", "current_period_end", "updated_at"])
    return subscription.customer


def _upsert_invoice_from_stripe(obj: dict, event_type: str):
    customer = _customer_from_provider_id(obj.get("customer", ""))
    if not customer:
        return None
    subscription = Subscription.objects.filter(provider="stripe", provider_subscription_id=obj.get("subscription", "")).first()
    status_map = {
        "paid": Invoice.Status.PAID,
        "open": Invoice.Status.OPEN,
        "draft": Invoice.Status.DRAFT,
        "void": Invoice.Status.VOID,
        "uncollectible": Invoice.Status.UNCOLLECTIBLE,
    }
    invoice, _ = Invoice.objects.update_or_create(
        provider="stripe",
        provider_invoice_id=obj.get("id", ""),
        defaults={
            "customer": customer,
            "subscription": subscription,
            "status": status_map.get(obj.get("status"), Invoice.Status.OPEN),
            "currency": (obj.get("currency") or "usd").upper(),
            "amount_due_cents": obj.get("amount_due") or 0,
            "amount_paid_cents": obj.get("amount_paid") or 0,
            "hosted_invoice_url": obj.get("hosted_invoice_url") or "",
            "due_at": _ts(obj.get("due_date")),
            "paid_at": _ts(obj.get("status_transitions", {}).get("paid_at")),
        },
    )
    if event_type == "invoice.payment_failed":
        retry_at = _ts(obj.get("next_payment_attempt"))
        open_or_update_dunning_case(customer=customer, subscription=subscription, invoice=invoice, retry_at=retry_at)
    return customer


def _upsert_payment_from_stripe(obj: dict, event_type: str):
    customer = _customer_from_provider_id(obj.get("customer", ""))
    if not customer:
        return None
    status_map = {
        "payment_intent.succeeded": PaymentTransaction.Status.SUCCEEDED,
        "payment_intent.payment_failed": PaymentTransaction.Status.FAILED,
        "payment_intent.processing": PaymentTransaction.Status.PROCESSING,
        "payment_intent.requires_action": PaymentTransaction.Status.REQUIRES_ACTION,
    }
    last_error = obj.get("last_payment_error") or {}
    PaymentTransaction.objects.update_or_create(
        provider="stripe",
        provider_payment_id=obj.get("id", ""),
        defaults={
            "customer": customer,
            "status": status_map.get(event_type, PaymentTransaction.Status.PROCESSING),
            "currency": (obj.get("currency") or "usd").upper(),
            "amount_cents": obj.get("amount") or 0,
            "failure_code": last_error.get("code", ""),
            "failure_message": last_error.get("message", ""),
            "metadata": obj.get("metadata") or {},
        },
    )
    return customer


def _mark_payment_refunded_from_charge(obj: dict):
    payment_intent_id = obj.get("payment_intent", "")
    payment = PaymentTransaction.objects.filter(provider="stripe", provider_payment_id=payment_intent_id).select_related("customer").first()
    if not payment:
        return _customer_from_provider_id(obj.get("customer", ""))
    payment.status = PaymentTransaction.Status.REFUNDED
    payment.metadata = {**(payment.metadata or {}), "stripe_charge_refund": obj.get("id", "")}
    payment.save(update_fields=["status", "metadata", "updated_at"])
    return payment.customer


def _ts(value):
    if not value:
        return None
    return datetime.fromtimestamp(value, tz=dt_timezone.utc)
