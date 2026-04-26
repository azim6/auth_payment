from decimal import Decimal
from django.test import TestCase
from billing.models import Plan
from tax_pricing.models import Currency, Region, TaxJurisdiction, RegionalPrice
from tax_pricing.services import resolve_plan_price


class TaxPricingTests(TestCase):
    def test_resolve_exclusive_tax_price(self):
        usd = Currency.objects.create(code="USD", name="US Dollar")
        region = Region.objects.create(code="US", name="United States", country_code="US", currency=usd)
        TaxJurisdiction.objects.create(code="US", name="United States", country_code="US", default_rate_percent=Decimal("10.0000"))
        plan = Plan.objects.create(name="Pro", slug="pro", description="Pro", is_active=True)
        RegionalPrice.objects.create(plan=plan, region=region, currency=usd, unit_amount=Decimal("100.00"), tax_behavior="exclusive")
        record = resolve_plan_price(plan, "US")
        self.assertEqual(record.tax_amount, Decimal("10.00"))
        self.assertEqual(record.total_amount, Decimal("110.00"))

    def test_resolve_tax_inclusive_price(self):
        eur = Currency.objects.create(code="EUR", name="Euro")
        region = Region.objects.create(code="EU", name="European Union", country_code="DE", currency=eur, is_tax_inclusive=True)
        TaxJurisdiction.objects.create(code="DE", name="Germany", country_code="DE", default_rate_percent=Decimal("19.0000"))
        plan = Plan.objects.create(name="Starter", slug="starter", description="Starter", is_active=True)
        RegionalPrice.objects.create(plan=plan, region=region, currency=eur, unit_amount=Decimal("119.00"), tax_behavior="inclusive")
        record = resolve_plan_price(plan, "EU")
        self.assertEqual(record.total_amount, Decimal("119.00"))
        self.assertTrue(record.tax_inclusive)
