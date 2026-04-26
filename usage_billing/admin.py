from django.contrib import admin

from .models import CreditApplication, CreditGrant, Meter, MeterPrice, RatedUsageLine, UsageAggregationWindow, UsageEvent, UsageReconciliationRun


@admin.register(Meter)
class MeterAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "unit", "aggregation", "is_active", "updated_at")
    search_fields = ("code", "name")
    list_filter = ("aggregation", "is_active")


@admin.register(MeterPrice)
class MeterPriceAdmin(admin.ModelAdmin):
    list_display = ("code", "meter", "pricing_model", "currency", "unit_amount_cents", "free_units", "is_active")
    search_fields = ("code", "meter__code")
    list_filter = ("pricing_model", "currency", "is_active")


@admin.register(UsageEvent)
class UsageEventAdmin(admin.ModelAdmin):
    list_display = ("organization", "meter", "quantity", "occurred_at", "source")
    search_fields = ("organization__slug", "meter__code", "idempotency_key")
    list_filter = ("meter", "source")


@admin.register(UsageAggregationWindow)
class UsageAggregationWindowAdmin(admin.ModelAdmin):
    list_display = ("organization", "subscription", "meter", "window_start", "window_end", "quantity", "status")
    search_fields = ("organization__slug", "meter__code")
    list_filter = ("status", "meter")


@admin.register(RatedUsageLine)
class RatedUsageLineAdmin(admin.ModelAdmin):
    list_display = ("window", "meter_price", "quantity", "billable_quantity", "amount_cents", "currency", "status")
    list_filter = ("status", "currency")


@admin.register(CreditGrant)
class CreditGrantAdmin(admin.ModelAdmin):
    list_display = ("organization", "currency", "original_amount_cents", "remaining_amount_cents", "status", "expires_at")
    search_fields = ("organization__slug", "reason")
    list_filter = ("status", "currency")


@admin.register(CreditApplication)
class CreditApplicationAdmin(admin.ModelAdmin):
    list_display = ("credit_grant", "rated_line", "amount_cents", "created_at")


@admin.register(UsageReconciliationRun)
class UsageReconciliationRunAdmin(admin.ModelAdmin):
    list_display = ("provider", "organization", "window_start", "window_end", "status", "local_total_cents", "provider_total_cents", "mismatch_count")
    list_filter = ("provider", "status")
