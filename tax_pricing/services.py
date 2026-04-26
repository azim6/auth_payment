from decimal import Decimal, ROUND_HALF_UP
from django.utils import timezone
from .models import RegionalPrice, TaxRate, TaxExemption, PriceResolutionRecord, Region


def money(value):
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def active_tax_rate(region, product_category=""):
    now = timezone.now()
    jurisdiction = region.taxjurisdiction_set.filter(is_active=True).first() if hasattr(region, "taxjurisdiction_set") else None
    if not jurisdiction and region.country_code:
        from .models import TaxJurisdiction
        jurisdiction = TaxJurisdiction.objects.filter(country_code=region.country_code, is_active=True).first()
    if not jurisdiction:
        return Decimal("0.0000")
    rate = TaxRate.objects.filter(
        jurisdiction=jurisdiction,
        is_active=True,
        valid_from__lte=now,
    ).filter(valid_until__isnull=True).order_by("-valid_from").first()
    return rate.rate_percent if rate else jurisdiction.default_rate_percent


def has_tax_exemption(region, organization=None, user=None):
    if not region.country_code:
        return False
    qs = TaxExemption.objects.filter(jurisdiction__country_code=region.country_code, is_active=True)
    if organization:
        qs = qs.filter(organization=organization)
    elif user:
        qs = qs.filter(user=user)
    else:
        return False
    now = timezone.now()
    return qs.filter(verified_at__isnull=False).filter(expires_at__isnull=True).exists() or qs.filter(verified_at__isnull=False, expires_at__gt=now).exists()


def resolve_plan_price(plan, region_code, organization=None, user=None):
    region = Region.objects.select_related("currency").get(code=region_code, is_active=True)
    regional_price = RegionalPrice.objects.select_related("currency").filter(
        plan=plan,
        region=region,
        is_active=True,
    ).order_by("-starts_at").first()
    if not regional_price:
        raise ValueError("No active regional price exists for this plan and region.")
    unit_amount = money(regional_price.unit_amount)
    rate_percent = Decimal("0.0000") if has_tax_exemption(region, organization, user) else active_tax_rate(region)
    if regional_price.tax_behavior == "inclusive" or region.is_tax_inclusive:
        tax_amount = money(unit_amount - (unit_amount / (Decimal("1.0") + (rate_percent / Decimal("100"))))) if rate_percent else Decimal("0.00")
        total_amount = unit_amount
        tax_inclusive = True
    else:
        tax_amount = money(unit_amount * rate_percent / Decimal("100"))
        total_amount = money(unit_amount + tax_amount)
        tax_inclusive = False
    return PriceResolutionRecord.objects.create(
        organization=organization,
        user=user,
        plan=plan,
        region=region,
        currency=regional_price.currency,
        unit_amount=unit_amount,
        tax_amount=tax_amount,
        total_amount=total_amount,
        tax_rate_percent=rate_percent,
        tax_inclusive=tax_inclusive,
        reason="regional_price_resolution_v32",
    )
