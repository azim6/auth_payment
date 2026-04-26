from __future__ import annotations

from dataclasses import dataclass

from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.utils import timezone

from accounts.models import Organization
from billing.models import BillingCustomer
from billing.services import build_customer_entitlements_with_addons, get_or_create_org_customer

from .catalog import BUSINESS_PRODUCTS, get_action_rule
from .models import ProductAccessDecision, ProductAccessOverride, ProductUsageEvent


@dataclass
class Subject:
    user: object | None = None
    organization: Organization | None = None
    customer: BillingCustomer | None = None


def period_key_for(period: str, now=None) -> str:
    now = now or timezone.now()
    if period == "day":
        return now.strftime("%Y-%m-%d")
    if period == "month":
        return now.strftime("%Y-%m")
    if period == "total":
        return "total"
    return ""


def resolve_subject(*, user_id=None, organization_slug=None, organization_id=None, actor=None) -> Subject:
    user = None
    org = None
    User = get_user_model()
    if user_id:
        user = User.objects.filter(id=user_id).first()
    if organization_slug:
        org = Organization.objects.filter(slug=organization_slug, is_active=True).first()
    elif organization_id:
        org = Organization.objects.filter(id=organization_id, is_active=True).first()
    if org:
        customer = get_or_create_org_customer(org, actor=actor or org.owner)
    elif user:
        customer, _ = BillingCustomer.objects.get_or_create(user=user, defaults={"billing_email": user.email, "billing_name": getattr(user, "full_name", "") or user.email})
    else:
        customer = None
    return Subject(user=user, organization=org, customer=customer)


def _subject_filter(subject: Subject) -> dict:
    if subject.organization:
        return {"organization": subject.organization}
    if subject.user:
        return {"user": subject.user}
    return {}


def active_overrides(subject: Subject, *, product: str, action: str, entitlement_key: str = ""):
    filters = _subject_filter(subject)
    if not filters:
        return ProductAccessOverride.objects.none()
    qs = ProductAccessOverride.objects.filter(**filters, product=product, is_active=True)
    qs = qs.filter(action__in=["", action])
    if entitlement_key:
        qs = qs.filter(entitlement_key__in=["", entitlement_key])
    now = timezone.now()
    return qs.filter(expires_at__isnull=True) | qs.filter(expires_at__gt=now)


def _entitlements(subject: Subject) -> dict:
    if not subject.customer:
        return {"features": {}, "subscriptions": []}
    return build_customer_entitlements_with_addons(subject.customer)


def _feature_value(features: dict, key: str):
    # v43 scoped project entitlements are stored as product.product.feature. The
    # catalog uses natural keys such as zatca.documents_per_month, so support both.
    direct = features.get(key)
    if direct is not None:
        return direct
    prefix = key.split(".", 1)[0]
    scoped_key = f"{prefix}.{key}"
    return features.get(scoped_key)


def usage_total(subject: Subject, *, product: str, action: str, period_key: str) -> int:
    filters = _subject_filter(subject)
    if not filters:
        return 0
    aggregate = ProductUsageEvent.objects.filter(**filters, product=product, action=action, period_key=period_key).aggregate(total=Sum("quantity"))
    return aggregate["total"] or 0


def record_usage(*, subject: Subject, product: str, action: str, quantity: int = 1, idempotency_key: str = "", source: str = "api", metadata: dict | None = None) -> ProductUsageEvent:
    metadata = metadata or {}
    filters = _subject_filter(subject)
    if idempotency_key:
        event, _ = ProductUsageEvent.objects.get_or_create(
            idempotency_key=idempotency_key,
            defaults={**filters, "product": product, "action": action, "quantity": quantity, "period_key": period_key_for(get_action_rule(product, action).get("period", "none") if get_action_rule(product, action) else "none"), "source": source, "metadata": metadata},
        )
        return event
    return ProductUsageEvent.objects.create(
        **filters,
        product=product,
        action=action,
        quantity=quantity,
        period_key=period_key_for(get_action_rule(product, action).get("period", "none") if get_action_rule(product, action) else "none"),
        source=source,
        metadata=metadata,
    )


def check_product_access(*, subject: Subject, product: str, action: str, quantity: int = 1, record_decision: bool = True) -> dict:
    if product not in BUSINESS_PRODUCTS:
        payload = {"allowed": False, "reason": "unknown_product", "product": product, "action": action}
        _record_decision(subject, payload, record_decision)
        return payload
    rule = get_action_rule(product, action)
    if not rule:
        payload = {"allowed": False, "reason": "unknown_action", "product": product, "action": action}
        _record_decision(subject, payload, record_decision)
        return payload
    if not subject.customer:
        payload = {"allowed": False, "reason": "unknown_subject", "product": product, "action": action}
        _record_decision(subject, payload, record_decision)
        return payload

    entitlement_payload = _entitlements(subject)
    features = entitlement_payload.get("features", {})
    plan_codes = [item.get("plan") for item in entitlement_payload.get("subscriptions", []) if item.get("project") in {product, "global"}]

    deny_override = active_overrides(subject, product=product, action=action).filter(effect=ProductAccessOverride.Effect.DENY).first()
    if deny_override:
        payload = {"allowed": False, "reason": "admin_denied", "product": product, "action": action, "plan_codes": plan_codes}
        _record_decision(subject, payload, record_decision)
        return payload

    allow_override = active_overrides(subject, product=product, action=action).filter(effect=ProductAccessOverride.Effect.ALLOW).first()
    required_key = rule.get("required")
    if required_key:
        required_value = _feature_value(features, required_key)
        if not required_value and not allow_override:
            payload = {"allowed": False, "reason": "missing_entitlement", "product": product, "action": action, "required": required_key, "plan_codes": plan_codes}
            _record_decision(subject, payload, record_decision)
            return payload

    limit_key = rule.get("limit")
    limit_value = None
    used = None
    remaining = None
    if limit_key:
        limit_override = active_overrides(subject, product=product, action=action, entitlement_key=limit_key).filter(effect=ProductAccessOverride.Effect.LIMIT).first()
        limit_value = limit_override.int_value if limit_override and limit_override.int_value is not None else _feature_value(features, limit_key)
        if limit_value is None:
            payload = {"allowed": False, "reason": "missing_limit", "product": product, "action": action, "limit_key": limit_key, "plan_codes": plan_codes}
            _record_decision(subject, payload, record_decision)
            return payload
        limit_value = int(limit_value)
        period = rule.get("period", "none")
        key = period_key_for(period)
        used = usage_total(subject, product=product, action=action, period_key=key)
        remaining = max(limit_value - used, 0)
        if used + quantity > limit_value and not allow_override:
            payload = {
                "allowed": False,
                "reason": "limit_exceeded",
                "product": product,
                "action": action,
                "limit": limit_value,
                "used": used,
                "remaining": remaining,
                "period_key": key,
                "plan_codes": plan_codes,
            }
            _record_decision(subject, payload, record_decision)
            return payload

    payload = {
        "allowed": True,
        "reason": "allowed",
        "product": product,
        "action": action,
        "limit": limit_value,
        "used": used,
        "remaining": remaining,
        "plan_codes": plan_codes,
        "required": required_key,
        "limit_key": limit_key,
    }
    _record_decision(subject, payload, record_decision)
    return payload


def _record_decision(subject: Subject, payload: dict, record_decision: bool) -> None:
    if not record_decision:
        return
    ProductAccessDecision.objects.create(
        user=subject.user,
        organization=subject.organization,
        product=payload.get("product", ""),
        action=payload.get("action", ""),
        allowed=bool(payload.get("allowed")),
        reason=payload.get("reason", ""),
        remaining=payload.get("remaining"),
        limit=payload.get("limit"),
        used=payload.get("used"),
        plan_codes=payload.get("plan_codes", []),
        metadata={k: v for k, v in payload.items() if k not in {"product", "action", "allowed", "reason", "remaining", "limit", "used", "plan_codes"}},
    )


def product_access_summary(subject: Subject) -> dict:
    entitlement_payload = _entitlements(subject)
    checks = {}
    for product, config in BUSINESS_PRODUCTS.items():
        checks[product] = {
            "name": config["name"],
            "actions": {
                action: check_product_access(subject=subject, product=product, action=action, record_decision=False)
                for action in config.get("actions", {})
            },
        }
    return {
        "subject": {
            "user_id": str(subject.user.id) if subject.user else None,
            "organization_id": str(subject.organization.id) if subject.organization else None,
            "organization_slug": subject.organization.slug if subject.organization else None,
        },
        "entitlements": entitlement_payload,
        "products": checks,
    }
