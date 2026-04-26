from __future__ import annotations

import hmac
from dataclasses import dataclass
from typing import Any

from django.conf import settings
from datetime import datetime, timezone as dt_timezone
from django.utils import timezone

try:
    import stripe
except Exception:  # pragma: no cover - optional dependency guard for local scaffolds
    stripe = None

from .models import BillingCustomer, Price


class BillingProviderError(RuntimeError):
    pass


@dataclass(frozen=True)
class ProviderCheckoutSession:
    provider_session_id: str
    url: str
    expires_at: object | None = None
    raw: dict[str, Any] | None = None


@dataclass(frozen=True)
class ProviderPortalSession:
    provider_session_id: str
    url: str
    raw: dict[str, Any] | None = None


class StripeBillingProvider:
    provider = "stripe"

    def __init__(self):
        self.secret_key = getattr(settings, "STRIPE_SECRET_KEY", "")
        self.webhook_secret = getattr(settings, "STRIPE_WEBHOOK_SECRET", "")
        if stripe is not None and self.secret_key:
            stripe.api_key = self.secret_key

    def _require_sdk(self):
        if stripe is None:
            raise BillingProviderError("stripe package is not installed.")
        if not self.secret_key:
            raise BillingProviderError("STRIPE_SECRET_KEY is not configured.")

    def ensure_customer(self, customer: BillingCustomer) -> str:
        self._require_sdk()
        if customer.provider == self.provider and customer.provider_customer_id:
            return customer.provider_customer_id
        created = stripe.Customer.create(
            email=customer.billing_email or None,
            name=customer.billing_name or None,
            metadata={
                "billing_customer_id": str(customer.id),
                "organization_id": str(customer.organization_id or ""),
                "user_id": str(customer.user_id or ""),
            },
        )
        customer.provider = self.provider
        customer.provider_customer_id = created["id"]
        customer.save(update_fields=["provider", "provider_customer_id", "updated_at"])
        return created["id"]

    def create_checkout_session(self, *, customer: BillingCustomer, price: Price, success_url: str, cancel_url: str, metadata: dict[str, str] | None = None) -> ProviderCheckoutSession:
        self._require_sdk()
        if not price.provider_price_id:
            raise BillingProviderError("Price is missing provider_price_id.")
        provider_customer_id = self.ensure_customer(customer)
        session = stripe.checkout.Session.create(
            mode="subscription" if price.interval in {Price.Interval.MONTH, Price.Interval.YEAR} else "payment",
            customer=provider_customer_id,
            line_items=[{"price": price.provider_price_id, "quantity": 1}],
            success_url=success_url,
            cancel_url=cancel_url,
            metadata=metadata or {},
            allow_promotion_codes=True,
        )
        expires_at = None
        if session.get("expires_at"):
            expires_at = datetime.fromtimestamp(session["expires_at"], tz=dt_timezone.utc)
        return ProviderCheckoutSession(provider_session_id=session["id"], url=session["url"], expires_at=expires_at, raw=dict(session))

    def create_portal_session(self, *, customer: BillingCustomer, return_url: str) -> ProviderPortalSession:
        self._require_sdk()
        provider_customer_id = self.ensure_customer(customer)
        session = stripe.billing_portal.Session.create(customer=provider_customer_id, return_url=return_url)
        return ProviderPortalSession(provider_session_id=session["id"], url=session["url"], raw=dict(session))

    def update_subscription_quantity(self, *, provider_subscription_id: str, quantity: int):
        """Update the first Stripe subscription item quantity.

        Complex multi-item subscription updates should be modeled explicitly
        before being enabled. v34 intentionally keeps this conservative.
        """
        self._require_sdk()
        subscription = stripe.Subscription.retrieve(provider_subscription_id)
        items = subscription.get("items", {}).get("data", [])
        if not items:
            raise BillingProviderError("Stripe subscription has no subscription items.")
        updated = stripe.Subscription.modify(provider_subscription_id, items=[{"id": items[0]["id"], "quantity": quantity}])
        return dict(updated)

    def cancel_subscription(self, *, provider_subscription_id: str, at_period_end: bool = True):
        self._require_sdk()
        if at_period_end:
            result = stripe.Subscription.modify(provider_subscription_id, cancel_at_period_end=True)
        else:
            result = stripe.Subscription.cancel(provider_subscription_id)
        return dict(result)

    def resume_subscription(self, *, provider_subscription_id: str):
        self._require_sdk()
        result = stripe.Subscription.modify(provider_subscription_id, cancel_at_period_end=False)
        return dict(result)

    def create_refund(self, *, provider_payment_id: str, amount_cents: int | None = None, reason: str = "requested_by_customer", metadata: dict | None = None):
        self._require_sdk()
        kwargs = {"payment_intent": provider_payment_id, "reason": reason, "metadata": metadata or {}}
        if amount_cents is not None:
            kwargs["amount"] = amount_cents
        result = stripe.Refund.create(**kwargs)
        return dict(result)

    def retrieve_subscription(self, *, provider_subscription_id: str):
        self._require_sdk()
        return dict(stripe.Subscription.retrieve(provider_subscription_id))

    def verify_webhook(self, payload: bytes, signature: str):
        self._require_sdk()
        if not self.webhook_secret:
            raise BillingProviderError("STRIPE_WEBHOOK_SECRET is not configured.")
        return stripe.Webhook.construct_event(payload=payload, sig_header=signature, secret=self.webhook_secret)


def get_billing_provider(provider: str = "stripe"):
    if provider == "stripe":
        return StripeBillingProvider()
    raise BillingProviderError(f"Unsupported billing provider: {provider}")


def constant_time_token_match(left: str, right: str) -> bool:
    return hmac.compare_digest(left or "", right or "")
