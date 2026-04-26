from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from accounts.models import Organization
from billing.models import Subscription
from .models import CreditApplication, CreditGrant, Meter, MeterPrice, RatedUsageLine, UsageAggregationWindow, UsageEvent, UsageReconciliationRun


def ingest_usage_event(*, organization_id, meter_code, quantity, idempotency_key, user=None, occurred_at=None, source="api", attributes=None):
    organization = Organization.objects.get(id=organization_id)
    meter = Meter.objects.get(code=meter_code, is_active=True)
    subscription = Subscription.objects.filter(customer__organization=organization, status__in=["trialing", "active", "free", "past_due"]).order_by("-created_at").first()
    event, _created = UsageEvent.objects.get_or_create(
        organization=organization,
        meter=meter,
        idempotency_key=idempotency_key,
        defaults={
            "user": user,
            "subscription": subscription,
            "quantity": quantity,
            "occurred_at": occurred_at or timezone.now(),
            "source": source,
            "attributes": attributes or {},
        },
    )
    return event


def aggregate_window(*, subscription, meter, window_start, window_end):
    events = UsageEvent.objects.filter(subscription=subscription, meter=meter, occurred_at__gte=window_start, occurred_at__lt=window_end)
    if meter.aggregation == Meter.Aggregation.MAX:
        quantity = max([event.quantity for event in events], default=Decimal("0"))
    elif meter.aggregation == Meter.Aggregation.LAST:
        last_event = events.order_by("-occurred_at").first()
        quantity = last_event.quantity if last_event else Decimal("0")
    elif meter.aggregation == Meter.Aggregation.UNIQUE:
        quantity = Decimal(str(events.values("attributes").distinct().count()))
    else:
        quantity = events.aggregate(total=Sum("quantity"))["total"] or Decimal("0")
    window, _created = UsageAggregationWindow.objects.update_or_create(
        subscription=subscription,
        meter=meter,
        window_start=window_start,
        window_end=window_end,
        defaults={"organization": subscription.customer.organization, "quantity": quantity, "status": UsageAggregationWindow.Status.OPEN},
    )
    return window


def cents_for_quantity(quantity, unit_amount_cents):
    return int((Decimal(quantity) * Decimal(unit_amount_cents)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


@transaction.atomic
def rate_usage_window(*, window, meter_price, apply_credits=True):
    free_units = meter_price.free_units or Decimal("0")
    billable_quantity = max(window.quantity - free_units, Decimal("0"))
    amount_cents = cents_for_quantity(billable_quantity, meter_price.unit_amount_cents)
    line, _created = RatedUsageLine.objects.update_or_create(
        window=window,
        defaults={
            "meter_price": meter_price,
            "quantity": window.quantity,
            "free_units_applied": min(window.quantity, free_units),
            "billable_quantity": billable_quantity,
            "currency": meter_price.currency,
            "amount_cents": amount_cents,
            "status": RatedUsageLine.Status.READY,
            "rating_details": {"pricing_model": meter_price.pricing_model, "unit_amount_cents": meter_price.unit_amount_cents},
        },
    )
    if apply_credits and line.amount_cents > 0:
        apply_available_credits(line)
    return line


def apply_available_credits(line):
    organization = line.window.organization
    remaining = line.amount_cents
    grants = CreditGrant.objects.select_for_update().filter(organization=organization, status=CreditGrant.Status.ACTIVE, currency=line.currency, remaining_amount_cents__gt=0).order_by("expires_at", "created_at")
    for grant in grants:
        if remaining <= 0:
            break
        amount = min(remaining, grant.remaining_amount_cents)
        CreditApplication.objects.create(credit_grant=grant, rated_line=line, amount_cents=amount)
        grant.remaining_amount_cents -= amount
        if grant.remaining_amount_cents == 0:
            grant.status = CreditGrant.Status.DEPLETED
        grant.save(update_fields=["remaining_amount_cents", "status", "updated_at"])
        remaining -= amount
    original_amount = line.amount_cents
    if remaining != original_amount:
        credits_applied = original_amount - remaining
        line.amount_cents = remaining
        line.rating_details = {**line.rating_details, "credits_applied_cents": line.rating_details.get("credits_applied_cents", 0) + credits_applied}
        line.save(update_fields=["amount_cents", "rating_details", "updated_at"])
    return line


def create_reconciliation_run(*, provider, window_start, window_end, organization=None, created_by=None):
    lines = RatedUsageLine.objects.filter(window__window_start__gte=window_start, window__window_end__lte=window_end)
    if organization:
        lines = lines.filter(window__organization=organization)
    local_total = lines.aggregate(total=Sum("amount_cents"))["total"] or 0
    return UsageReconciliationRun.objects.create(
        provider=provider,
        organization=organization,
        window_start=window_start,
        window_end=window_end,
        status=UsageReconciliationRun.Status.COMPLETED,
        local_total_cents=local_total,
        provider_total_cents=0,
        mismatch_count=0,
        report={"note": "Provider comparison adapter can populate provider totals."},
        created_by=created_by,
        completed_at=timezone.now(),
    )
