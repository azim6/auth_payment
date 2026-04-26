from django.contrib import admin
from .models import (
    Currency, Region, ExchangeRateSnapshot, TaxJurisdiction, TaxRate, TaxExemption,
    RegionalPrice, LocalizedInvoiceSetting, PriceResolutionRecord,
)


@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "minor_unit", "is_active")
    search_fields = ("code", "name")
    list_filter = ("is_active",)


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "country_code", "currency", "is_tax_inclusive", "is_active")
    search_fields = ("code", "name", "country_code")
    list_filter = ("is_active", "is_tax_inclusive", "currency")


@admin.register(ExchangeRateSnapshot)
class ExchangeRateSnapshotAdmin(admin.ModelAdmin):
    list_display = ("base_currency", "quote_currency", "rate", "source", "effective_at", "expires_at")
    list_filter = ("source", "base_currency", "quote_currency")


@admin.register(TaxJurisdiction)
class TaxJurisdictionAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "country_code", "tax_label", "default_rate_percent", "is_active")
    list_filter = ("country_code", "is_active")
    search_fields = ("code", "name")


@admin.register(TaxRate)
class TaxRateAdmin(admin.ModelAdmin):
    list_display = ("jurisdiction", "name", "rate_percent", "product_category", "valid_from", "valid_until", "is_active")
    list_filter = ("is_active", "jurisdiction")


@admin.register(TaxExemption)
class TaxExemptionAdmin(admin.ModelAdmin):
    list_display = ("organization", "user", "jurisdiction", "exemption_type", "verified_at", "expires_at", "is_active")
    list_filter = ("is_active", "exemption_type", "jurisdiction")
    search_fields = ("certificate_number", "organization__name", "user__email")


@admin.register(RegionalPrice)
class RegionalPriceAdmin(admin.ModelAdmin):
    list_display = ("plan", "region", "currency", "unit_amount", "interval", "tax_behavior", "is_active")
    list_filter = ("is_active", "interval", "tax_behavior", "region", "currency")


@admin.register(LocalizedInvoiceSetting)
class LocalizedInvoiceSettingAdmin(admin.ModelAdmin):
    list_display = ("region", "invoice_language", "invoice_prefix", "requires_buyer_tax_id")


@admin.register(PriceResolutionRecord)
class PriceResolutionRecordAdmin(admin.ModelAdmin):
    list_display = ("plan", "region", "currency", "unit_amount", "tax_amount", "total_amount", "created_at")
    list_filter = ("region", "currency", "tax_inclusive")
    readonly_fields = ("created_at",)
