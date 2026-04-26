from decimal import Decimal

import pytest

from billing.models import AddOn, AddOnEntitlement, Discount, Price, Project, SubscriptionAddOn
from billing.services import attach_subscription_addon, build_customer_entitlements_with_addons, redeem_discount


@pytest.mark.django_db
def test_percent_discount_calculates_amount():
    discount = Discount.objects.create(
        code="launch-20",
        name="Launch 20%",
        discount_type=Discount.DiscountType.PERCENT,
        percent_off=Decimal("20.00"),
    )
    assert discount.calculate_amount_cents(10000) == 2000


@pytest.mark.django_db
def test_addon_extends_integer_entitlement(subscription, user):
    project = Project.objects.create(code="api", name="API")
    addon = AddOn.objects.create(project=project, code="extra-api-100k", name="Extra API Requests", unit_amount_cents=1000)
    AddOnEntitlement.objects.create(addon=addon, key="requests.monthly.max", int_value=100000)
    attach_subscription_addon(subscription=subscription, addon=addon, quantity=2, actor=user)

    payload = build_customer_entitlements_with_addons(subscription.customer)
    assert payload["features"]["api.requests.monthly.max"] == 200000


@pytest.mark.django_db
def test_discount_redemption_is_idempotent(customer, user, plan):
    price = Price.objects.create(plan=plan, code="pro-monthly", amount_cents=10000)
    discount = Discount.objects.create(code="free-test", name="Free Test", discount_type=Discount.DiscountType.FREE)
    first = redeem_discount(customer=customer, price=price, discount_code=discount.code, idempotency_key="same", actor=user)
    second = redeem_discount(customer=customer, price=price, discount_code=discount.code, idempotency_key="same", actor=user)
    assert first.id == second.id
    assert first.final_amount_cents == 0
