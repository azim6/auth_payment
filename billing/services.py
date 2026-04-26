from django.db import models, transaction
from django.utils import timezone

from accounts.models import AuditLog, Organization, OrganizationMembership
from accounts.authorization import user_has_permission
from .models import BillingCustomer, BillingProfile, CreditNote, DunningCase, Entitlement, Plan, Price, RefundRequest, Subscription, Discount, PromotionCode, DiscountRedemption, AddOn, SubscriptionAddOn, EntitlementSnapshot, BillingOutboxEvent, ProviderSyncState, WebhookReplayRequest, EntitlementChangeLog

BILLING_PERMISSION = "billing.manage"


def can_manage_billing(user, organization: Organization) -> bool:
    if not user or not user.is_authenticated:
        return False
    if user.is_staff:
        return True
    membership = OrganizationMembership.objects.filter(organization=organization, user=user, is_active=True).first()
    if membership and membership.role == OrganizationMembership.Role.OWNER:
        return True
    return user_has_permission(user, organization, BILLING_PERMISSION)


def get_or_create_org_customer(organization: Organization, actor=None) -> BillingCustomer:
    customer, _ = BillingCustomer.objects.get_or_create(
        organization=organization,
        defaults={
            "billing_email": getattr(organization.owner, "email", ""),
            "billing_name": organization.name,
            "provider": "manual",
        },
    )
    return customer


def entitlement_value(entitlement: Entitlement):
    return entitlement.value


def build_effective_entitlements(subscription: Subscription) -> dict:
    """Plan entitlements plus subscription-level overrides."""
    entitlements = {}
    for item in subscription.plan.entitlements.all():
        entitlements[item.key] = entitlement_value(item)
    for item in subscription.entitlements.all():
        entitlements[item.key] = entitlement_value(item)
    return entitlements


def active_subscriptions_for_customer(customer: BillingCustomer):
    return customer.subscriptions.select_related("plan", "price", "plan__project").filter(
        status__in=[Subscription.Status.ACTIVE, Subscription.Status.TRIALING, Subscription.Status.FREE]
    )


def build_customer_entitlements(customer: BillingCustomer) -> dict:
    result = {"customer_id": str(customer.id), "subscriptions": [], "features": {}}
    for subscription in active_subscriptions_for_customer(customer):
        if not subscription.is_entitled:
            continue
        features = build_effective_entitlements(subscription)
        project_code = subscription.plan.project.code if subscription.plan.project_id else "global"
        result["subscriptions"].append({
            "subscription_id": str(subscription.id),
            "status": subscription.status,
            "plan": subscription.plan.code,
            "project": project_code,
            "current_period_end": subscription.current_period_end,
            "features": features,
        })
        for key, value in features.items():
            scoped_key = f"{project_code}.{key}" if project_code != "global" else key
            result["features"][scoped_key] = value
    return result


@transaction.atomic
def grant_manual_subscription(*, organization: Organization, plan: Plan, actor, price: Price | None = None, status: str = Subscription.Status.FREE, current_period_end=None, admin_note: str = "") -> Subscription:
    customer = get_or_create_org_customer(organization, actor=actor)
    subscription = Subscription.objects.create(
        customer=customer,
        plan=plan,
        price=price,
        status=status,
        provider="manual",
        current_period_start=timezone.now(),
        current_period_end=current_period_end,
        admin_note=admin_note,
        created_by=actor,
    )
    AuditLog.objects.create(
        actor=actor,
        category=AuditLog.Category.ADMIN,
        action="billing.subscription.grant_manual",
        outcome=AuditLog.Outcome.SUCCESS,
        subject_user_id=organization.owner_id,
        metadata={"organization_id": str(organization.id), "plan": plan.code, "subscription_id": str(subscription.id)},
    )
    return subscription


def record_usage(*, customer: BillingCustomer, metric, quantity: int = 1, idempotency_key: str = "", source: str = "api", metadata=None):
    """Create an append-only usage record with optional idempotency."""
    from .models import UsageRecord
    metadata = metadata or {}
    if idempotency_key:
        record, _ = UsageRecord.objects.get_or_create(
            customer=customer,
            metric=metric,
            idempotency_key=idempotency_key,
            defaults={"quantity": quantity, "source": source, "metadata": metadata},
        )
        return record
    return UsageRecord.objects.create(customer=customer, metric=metric, quantity=quantity, source=source, metadata=metadata)


def usage_total_for_period(*, customer: BillingCustomer, metric, start, end):
    from django.db.models import Sum, Max
    qs = customer.usage_records.filter(metric=metric, occurred_at__gte=start, occurred_at__lt=end)
    if metric.aggregation == metric.Aggregation.MAX:
        return qs.aggregate(value=Max("quantity"))["value"] or 0
    if metric.aggregation == metric.Aggregation.LAST:
        latest = qs.order_by("-occurred_at").first()
        return latest.quantity if latest else 0
    return qs.aggregate(value=Sum("quantity"))["value"] or 0



def _sync_subscription_change_to_provider(subscription: Subscription, change) -> dict:
    """Apply provider-side parts of supported subscription operations.

    Manual subscriptions stay local. Stripe subscriptions are synced for quantity
    changes, cancellation, and resume. Plan swaps remain local until a concrete
    provider price-item strategy is supplied.
    """
    if subscription.provider != "stripe" or not subscription.provider_subscription_id:
        return {"provider_sync": "not_required"}
    if change.metadata.get("skip_provider_sync") is True:
        return {"provider_sync": "skipped_by_metadata"}
    from .payment_providers import get_billing_provider
    provider = get_billing_provider("stripe")
    if change.action == change.Action.CHANGE_QUANTITY:
        return provider.update_subscription_quantity(provider_subscription_id=subscription.provider_subscription_id, quantity=change.target_quantity)
    if change.action == change.Action.CANCEL_AT_PERIOD_END:
        return provider.cancel_subscription(provider_subscription_id=subscription.provider_subscription_id, at_period_end=True)
    if change.action == change.Action.CANCEL_NOW:
        return provider.cancel_subscription(provider_subscription_id=subscription.provider_subscription_id, at_period_end=False)
    if change.action == change.Action.RESUME:
        return provider.resume_subscription(provider_subscription_id=subscription.provider_subscription_id)
    return {"provider_sync": "local_only", "reason": "action_not_supported_by_v34_provider_sync"}

def apply_subscription_change(change):
    """Apply a manual/admin subscription operation and leave a durable audit trail."""
    subscription = change.subscription
    now = timezone.now()
    action = change.action
    provider_result = _sync_subscription_change_to_provider(subscription, change)
    if action == change.Action.CHANGE_PLAN:
        if not change.target_plan:
            raise ValueError("target_plan is required for change_plan")
        subscription.plan = change.target_plan
        if change.target_price:
            subscription.price = change.target_price
    elif action == change.Action.CHANGE_QUANTITY:
        if not change.target_quantity:
            raise ValueError("target_quantity is required for change_quantity")
        subscription.quantity = change.target_quantity
        subscription.seat_limit = change.target_quantity
    elif action == change.Action.CANCEL_AT_PERIOD_END:
        subscription.cancel_at_period_end = True
    elif action == change.Action.CANCEL_NOW:
        subscription.status = Subscription.Status.CANCELLED
        subscription.cancelled_at = now
        subscription.current_period_end = now
    elif action == change.Action.RESUME:
        subscription.cancel_at_period_end = False
        if subscription.status in {Subscription.Status.CANCELLED, Subscription.Status.EXPIRED, Subscription.Status.PAUSED}:
            subscription.status = Subscription.Status.ACTIVE
            subscription.cancelled_at = None
    elif action == change.Action.EXTEND_TRIAL:
        subscription.status = Subscription.Status.TRIALING
        subscription.trial_ends_at = change.effective_at
    elif action == change.Action.EXTEND_GRACE:
        subscription.grace_period_ends_at = change.effective_at
    else:
        raise ValueError(f"Unsupported subscription change action: {action}")
    subscription.save()
    change.status = change.Status.APPLIED
    change.applied_at = now
    change.provider = subscription.provider
    change.provider_change_id = str(provider_result.get("id", "")) if isinstance(provider_result, dict) else ""
    change.metadata = {**(change.metadata or {}), "provider_result": provider_result}
    change.save(update_fields=["status", "applied_at", "provider", "provider_change_id", "metadata", "updated_at"])
    EntitlementSnapshot.objects.filter(customer=subscription.customer).update(invalidated_at=now, reason="subscription_changed")
    AuditLog.objects.create(
        actor=change.requested_by,
        category=AuditLog.Category.ADMIN,
        action=f"billing.subscription.{action}",
        outcome=AuditLog.Outcome.SUCCESS,
        metadata={"subscription_id": str(subscription.id), "change_id": str(change.id)},
    )
    return subscription


@transaction.atomic
def get_or_create_billing_profile(customer: BillingCustomer) -> BillingProfile:
    profile, _ = BillingProfile.objects.get_or_create(
        customer=customer,
        defaults={
            "legal_name": customer.billing_name,
            "billing_email": customer.billing_email,
            "default_currency": "USD",
        },
    )
    return profile


def next_customer_invoice_number(customer: BillingCustomer, prefix: str = "INV") -> str:
    """Reserve a sequential invoice/credit-note number per billing customer."""
    profile = get_or_create_billing_profile(customer)
    actual_prefix = profile.invoice_prefix or prefix
    number = f"{actual_prefix}-{profile.next_invoice_number:06d}"
    profile.next_invoice_number += 1
    profile.save(update_fields=["next_invoice_number", "updated_at"])
    return number


@transaction.atomic
def issue_credit_note(*, customer: BillingCustomer, amount_cents: int, actor, invoice=None, reason=None, currency="USD", memo="", metadata=None) -> CreditNote:
    credit = CreditNote.objects.create(
        customer=customer,
        invoice=invoice,
        number=next_customer_invoice_number(customer, prefix="CN"),
        reason=reason or CreditNote.Reason.OTHER,
        status=CreditNote.Status.ISSUED,
        currency=currency,
        amount_cents=amount_cents,
        memo=memo,
        metadata=metadata or {},
        issued_by=actor,
        issued_at=timezone.now(),
    )
    AuditLog.objects.create(
        actor=actor,
        category=AuditLog.Category.ADMIN,
        action="billing.credit_note.issued",
        outcome=AuditLog.Outcome.SUCCESS,
        metadata={"credit_note_id": str(credit.id), "customer_id": str(customer.id), "amount_cents": amount_cents},
    )
    return credit


@transaction.atomic
def review_refund_request(*, refund: RefundRequest, actor, action: str, note: str = "", provider_refund_id: str = "") -> RefundRequest:
    now = timezone.now()
    if action == "approve":
        refund.status = RefundRequest.Status.APPROVED
        refund.reviewed_by = actor
        refund.reviewed_at = now
    elif action == "reject":
        refund.status = RefundRequest.Status.REJECTED
        refund.reviewed_by = actor
        refund.reviewed_at = now
        refund.error = note
    elif action == "process":
        if refund.payment_id and refund.payment.provider == "stripe" and not provider_refund_id:
            from .payment_providers import get_billing_provider
            provider_result = get_billing_provider("stripe").create_refund(
                provider_payment_id=refund.payment.provider_payment_id,
                amount_cents=refund.amount_cents,
                metadata={"refund_request_id": str(refund.id), "billing_customer_id": str(refund.customer_id)},
            )
            provider_refund_id = provider_result.get("id", "")
        refund.status = RefundRequest.Status.PROCESSED
        refund.reviewed_by = actor
        refund.reviewed_at = refund.reviewed_at or now
        refund.processed_at = now
        refund.provider_refund_id = provider_refund_id
        if refund.payment_id:
            refund.payment.status = refund.payment.Status.REFUNDED
            refund.payment.save(update_fields=["status", "updated_at"])
    else:
        raise ValueError("Unsupported refund action")
    refund.save()
    AuditLog.objects.create(
        actor=actor,
        category=AuditLog.Category.ADMIN,
        action=f"billing.refund.{action}",
        outcome=AuditLog.Outcome.SUCCESS,
        metadata={"refund_id": str(refund.id), "customer_id": str(refund.customer_id)},
    )
    return refund


def open_or_update_dunning_case(*, customer: BillingCustomer, subscription=None, invoice=None, failure_time=None, retry_at=None, grace_ends_at=None) -> DunningCase:
    case = DunningCase.objects.filter(customer=customer, subscription=subscription, invoice=invoice).exclude(status__in=[DunningCase.Status.RESOLVED, DunningCase.Status.CANCELLED]).first()
    if not case:
        case = DunningCase(customer=customer, subscription=subscription, invoice=invoice)
    case.failed_attempts += 1
    case.last_failure_at = failure_time or timezone.now()
    case.next_retry_at = retry_at
    case.grace_ends_at = grace_ends_at
    if grace_ends_at:
        case.status = DunningCase.Status.IN_GRACE
    case.save()
    return case


@transaction.atomic
def redeem_discount(*, customer: BillingCustomer, price: Price, actor, promotion_code: str = "", discount_code: str = "", idempotency_key: str = "") -> DiscountRedemption:
    """Validate and redeem a discount/promotion code without charging the provider directly."""
    promo = None
    if promotion_code:
        promo = PromotionCode.objects.select_for_update().select_related("discount").get(code=promotion_code, is_active=True)
        discount = promo.discount
        if promo.organization_id and customer.organization_id and promo.organization_id != customer.organization_id:
            raise ValueError("Promotion code is not valid for this organization.")
        if not promo.is_redeemable:
            raise ValueError("Promotion code is not redeemable.")
    else:
        discount = Discount.objects.select_for_update().get(code=discount_code, is_active=True)
        if not discount.is_redeemable:
            raise ValueError("Discount is not redeemable.")
    if not discount.applies_to_price(price):
        raise ValueError("Discount does not apply to this price.")
    if idempotency_key:
        existing = DiscountRedemption.objects.filter(customer=customer, discount=discount, idempotency_key=idempotency_key).first()
        if existing:
            return existing
    original_amount = price.amount_cents
    discount_amount = discount.calculate_amount_cents(original_amount)
    redemption = DiscountRedemption.objects.create(
        customer=customer,
        discount=discount,
        promotion_code=promo,
        price=price,
        idempotency_key=idempotency_key,
        original_amount_cents=original_amount,
        discount_amount_cents=discount_amount,
        final_amount_cents=max(original_amount - discount_amount, 0),
        redeemed_by=actor,
    )
    discount.redeemed_count += 1
    discount.save(update_fields=["redeemed_count", "updated_at"])
    if promo:
        promo.redeemed_count += 1
        promo.save(update_fields=["redeemed_count", "updated_at"])
    AuditLog.objects.create(
        actor=actor,
        category=AuditLog.Category.ADMIN,
        action="billing.discount.redeemed",
        outcome=AuditLog.Outcome.SUCCESS,
        metadata={"customer_id": str(customer.id), "discount": discount.code, "redemption_id": str(redemption.id)},
    )
    return redemption


def _merge_addon_entitlements(base: dict, subscription: Subscription) -> dict:
    """Apply active subscription add-ons to the effective entitlement dict."""
    for subscription_addon in subscription.addons.select_related("addon").prefetch_related("addon__entitlements").filter(status=SubscriptionAddOn.Status.ACTIVE):
        project_code = subscription_addon.addon.project.code if subscription_addon.addon.project_id else None
        for item in subscription_addon.addon.entitlements.all():
            key = f"{project_code}.{item.key}" if project_code else item.key
            value = item.value
            if item.is_incremental and item.value_type == Entitlement.ValueType.INTEGER:
                base[key] = int(base.get(key, 0) or 0) + int(value or 0) * subscription_addon.quantity
            elif item.value_type == Entitlement.ValueType.BOOLEAN:
                base[key] = bool(base.get(key, False) or value)
            else:
                base[key] = value
    return base


@transaction.atomic
def attach_subscription_addon(*, subscription: Subscription, addon: AddOn, actor, quantity: int = 1, unit_amount_cents: int | None = None, current_period_end=None, metadata=None) -> SubscriptionAddOn:
    """Attach or update an add-on and invalidate the cached entitlement snapshot."""
    subscription_addon, _ = SubscriptionAddOn.objects.update_or_create(
        subscription=subscription,
        addon=addon,
        defaults={
            "status": SubscriptionAddOn.Status.ACTIVE,
            "quantity": quantity,
            "unit_amount_cents": addon.unit_amount_cents if unit_amount_cents is None else unit_amount_cents,
            "current_period_end": current_period_end,
            "created_by": actor,
            "metadata": metadata or {},
        },
    )
    EntitlementSnapshot.objects.filter(customer=subscription.customer).update(invalidated_at=timezone.now(), reason="subscription_addon_changed")
    AuditLog.objects.create(
        actor=actor,
        category=AuditLog.Category.ADMIN,
        action="billing.addon.attached",
        outcome=AuditLog.Outcome.SUCCESS,
        metadata={"subscription_id": str(subscription.id), "addon": addon.code, "quantity": quantity},
    )
    return subscription_addon


def build_customer_entitlements_with_addons(customer: BillingCustomer) -> dict:
    """Entitlement payload that includes plan, subscription overrides, and add-ons."""
    result = build_customer_entitlements(customer)
    for subscription in active_subscriptions_for_customer(customer).prefetch_related("addons__addon__entitlements"):
        if not subscription.is_entitled:
            continue
        result["features"] = _merge_addon_entitlements(result["features"], subscription)
    return result


@transaction.atomic
def recalculate_entitlement_snapshot(*, customer: BillingCustomer, reason: str = "manual") -> EntitlementSnapshot:
    payload = build_customer_entitlements_with_addons(customer)
    previous = EntitlementSnapshot.objects.filter(customer=customer).first()
    version = (previous.version + 1) if previous else 1
    snapshot, _ = EntitlementSnapshot.objects.update_or_create(
        customer=customer,
        defaults={
            "payload": payload,
            "version": version,
            "calculated_at": timezone.now(),
            "invalidated_at": None,
            "reason": reason,
        },
    )
    return snapshot


@transaction.atomic
def enqueue_billing_outbox_event(*, event_type: str, payload: dict | None = None, aggregate_type: str = "", aggregate_id: str = "", idempotency_key: str = "", headers: dict | None = None) -> BillingOutboxEvent:
    """Create a reliable outbox event inside the same DB transaction as billing state changes."""
    if idempotency_key:
        existing = BillingOutboxEvent.objects.filter(event_type=event_type, idempotency_key=idempotency_key).first()
        if existing:
            return existing
    return BillingOutboxEvent.objects.create(
        event_type=event_type,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        payload=payload or {},
        headers=headers or {},
        idempotency_key=idempotency_key,
    )


@transaction.atomic
def dispatch_due_outbox_events(*, limit: int = 50, event_type: str = "") -> dict:
    """Mark due outbox records as dispatched.

    v15 keeps provider delivery implementation intentionally small: production projects can replace
    this with HTTP/SQS/Kafka delivery while retaining the same DB contract and retry state.
    """
    now = timezone.now()
    qs = BillingOutboxEvent.objects.select_for_update(skip_locked=True).filter(
        status__in=[BillingOutboxEvent.Status.PENDING, BillingOutboxEvent.Status.FAILED],
        next_attempt_at__lte=now,
        attempts__lt=models.F("max_attempts"),
    )
    if event_type:
        qs = qs.filter(event_type=event_type)
    events = list(qs.order_by("next_attempt_at", "created_at")[:limit])
    dispatched = failed = 0
    for event in events:
        event.status = BillingOutboxEvent.Status.PROCESSING
        event.locked_at = now
        event.attempts += 1
        event.save(update_fields=["status", "locked_at", "attempts", "updated_at"])
        try:
            # Provider/bus delivery hook belongs here. The scaffold records success safely.
            event.status = BillingOutboxEvent.Status.DISPATCHED
            event.dispatched_at = timezone.now()
            event.last_error = ""
            dispatched += 1
        except Exception as exc:  # pragma: no cover - hook placeholder
            event.status = BillingOutboxEvent.Status.FAILED
            event.last_error = str(exc)
            event.next_attempt_at = timezone.now() + timezone.timedelta(minutes=min(60, 2 ** event.attempts))
            failed += 1
        event.locked_at = None
        event.save(update_fields=["status", "dispatched_at", "last_error", "next_attempt_at", "locked_at", "updated_at"])
    return {"selected": len(events), "dispatched": dispatched, "failed": failed}


def update_provider_sync_success(*, provider: str, resource_type: str, cursor: str = "", lag_seconds: int = 0, metadata: dict | None = None) -> ProviderSyncState:
    state, _ = ProviderSyncState.objects.get_or_create(provider=provider, resource_type=resource_type)
    state.status = ProviderSyncState.Status.HEALTHY
    state.cursor = cursor or state.cursor
    state.last_started_at = state.last_started_at or timezone.now()
    state.last_success_at = timezone.now()
    state.last_error = ""
    state.error_count = 0
    state.lag_seconds = lag_seconds
    if metadata:
        state.metadata.update(metadata)
    state.save()
    return state


def update_provider_sync_failure(*, provider: str, resource_type: str, error: str) -> ProviderSyncState:
    state, _ = ProviderSyncState.objects.get_or_create(provider=provider, resource_type=resource_type)
    state.status = ProviderSyncState.Status.FAILING if state.error_count >= 2 else ProviderSyncState.Status.DEGRADED
    state.last_failure_at = timezone.now()
    state.last_error = error
    state.error_count += 1
    state.save()
    return state


@transaction.atomic
def create_webhook_replay_request(*, webhook_event: BillingWebhookEvent, actor, reason: str = "", process_now: bool = False) -> WebhookReplayRequest:
    replay = WebhookReplayRequest.objects.create(webhook_event=webhook_event, requested_by=actor, reason=reason)
    if process_now:
        return replay_webhook_request(replay)
    return replay


@transaction.atomic
def replay_webhook_request(replay: WebhookReplayRequest) -> WebhookReplayRequest:
    """Replay a stored webhook event through the provider-specific processor."""
    from .webhooks import process_stripe_event
    try:
        if replay.webhook_event.provider == "stripe":
            process_stripe_event(dict(replay.webhook_event.payload), signature_valid=replay.webhook_event.signature_valid)
        else:
            raise ValueError(f"No replay handler configured for provider {replay.webhook_event.provider}.")
        replay.status = WebhookReplayRequest.Status.REPLAYED
        replay.replayed_at = timezone.now()
        replay.error = ""
    except Exception as exc:
        replay.status = WebhookReplayRequest.Status.FAILED
        replay.error = str(exc)
    replay.save(update_fields=["status", "replayed_at", "error", "updated_at"])
    return replay


@transaction.atomic
def recalculate_entitlement_snapshot_with_log(*, customer: BillingCustomer, reason: str = "manual", actor=None, metadata: dict | None = None) -> EntitlementSnapshot:
    previous = EntitlementSnapshot.objects.filter(customer=customer).first()
    previous_payload = previous.payload if previous else {}
    snapshot = recalculate_entitlement_snapshot(customer=customer, reason=reason)
    EntitlementChangeLog.objects.create(
        customer=customer,
        snapshot=snapshot,
        previous_payload=previous_payload,
        new_payload=snapshot.payload,
        reason=reason,
        changed_by=actor,
        metadata=metadata or {},
    )
    enqueue_billing_outbox_event(
        event_type="billing.entitlements.changed",
        aggregate_type="billing_customer",
        aggregate_id=str(customer.id),
        payload={"customer_id": str(customer.id), "snapshot_id": str(snapshot.id), "reason": reason, "version": snapshot.version},
        idempotency_key=f"entitlements:{customer.id}:{snapshot.version}",
    )
    return snapshot
