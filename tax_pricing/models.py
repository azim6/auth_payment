from decimal import Decimal
from django.conf import settings
from django.db import models
from django.utils import timezone


class Currency(models.Model):
    code = models.CharField(max_length=3, unique=True)
    name = models.CharField(max_length=80)
    minor_unit = models.PositiveSmallIntegerField(default=2)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.code


class Region(models.Model):
    code = models.CharField(max_length=16, unique=True)
    name = models.CharField(max_length=120)
    country_code = models.CharField(max_length=2, blank=True)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, related_name="regions")
    is_tax_inclusive = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.code


class ExchangeRateSnapshot(models.Model):
    base_currency = models.ForeignKey(Currency, on_delete=models.PROTECT, related_name="fx_base_snapshots")
    quote_currency = models.ForeignKey(Currency, on_delete=models.PROTECT, related_name="fx_quote_snapshots")
    rate = models.DecimalField(max_digits=18, decimal_places=8)
    source = models.CharField(max_length=80, default="manual")
    effective_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        indexes = [models.Index(fields=["base_currency", "quote_currency", "effective_at"])]


class TaxJurisdiction(models.Model):
    code = models.CharField(max_length=40, unique=True)
    name = models.CharField(max_length=160)
    country_code = models.CharField(max_length=2)
    region_code = models.CharField(max_length=32, blank=True)
    tax_label = models.CharField(max_length=40, default="VAT/GST")
    default_rate_percent = models.DecimalField(max_digits=7, decimal_places=4, default=Decimal("0.0000"))
    requires_tax_id = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.code


class TaxRate(models.Model):
    jurisdiction = models.ForeignKey(TaxJurisdiction, on_delete=models.CASCADE, related_name="rates")
    name = models.CharField(max_length=120)
    rate_percent = models.DecimalField(max_digits=7, decimal_places=4)
    product_category = models.CharField(max_length=80, blank=True)
    valid_from = models.DateTimeField(default=timezone.now)
    valid_until = models.DateTimeField(null=True, blank=True)
    is_reverse_charge = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)


class TaxExemption(models.Model):
    organization = models.ForeignKey("accounts.Organization", null=True, blank=True, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE)
    jurisdiction = models.ForeignKey(TaxJurisdiction, on_delete=models.PROTECT)
    exemption_type = models.CharField(max_length=40, default="resale")
    certificate_number = models.CharField(max_length=120, blank=True)
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, related_name="verified_tax_exemptions", on_delete=models.SET_NULL)
    verified_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class RegionalPrice(models.Model):
    plan = models.ForeignKey("billing.Plan", on_delete=models.CASCADE, related_name="regional_prices")
    region = models.ForeignKey(Region, on_delete=models.PROTECT)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT)
    unit_amount = models.DecimalField(max_digits=12, decimal_places=2)
    interval = models.CharField(max_length=20, default="month")
    tax_behavior = models.CharField(max_length=20, default="exclusive")
    provider_price_id = models.CharField(max_length=160, blank=True)
    starts_at = models.DateTimeField(default=timezone.now)
    ends_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = [("plan", "region", "currency", "interval")]


class LocalizedInvoiceSetting(models.Model):
    region = models.OneToOneField(Region, on_delete=models.CASCADE, related_name="invoice_settings")
    invoice_language = models.CharField(max_length=12, default="en")
    invoice_prefix = models.CharField(max_length=20, default="INV")
    tax_number_label = models.CharField(max_length=60, default="Tax ID")
    footer_text = models.TextField(blank=True)
    requires_buyer_tax_id = models.BooleanField(default=False)
    requires_seller_tax_id = models.BooleanField(default=False)


class PriceResolutionRecord(models.Model):
    organization = models.ForeignKey("accounts.Organization", null=True, blank=True, on_delete=models.SET_NULL)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    plan = models.ForeignKey("billing.Plan", on_delete=models.PROTECT)
    region = models.ForeignKey(Region, on_delete=models.PROTECT)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT)
    unit_amount = models.DecimalField(max_digits=12, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    tax_rate_percent = models.DecimalField(max_digits=7, decimal_places=4, default=Decimal("0.0000"))
    tax_inclusive = models.BooleanField(default=False)
    reason = models.CharField(max_length=160, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
