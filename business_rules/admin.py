from django.contrib import admin

from .models import ProductAccessDecision, ProductAccessOverride, ProductUsageEvent


@admin.register(ProductAccessOverride)
class ProductAccessOverrideAdmin(admin.ModelAdmin):
    list_display = ("product", "action", "effect", "user", "organization", "is_active", "expires_at", "created_at")
    list_filter = ("product", "effect", "is_active")
    search_fields = ("product", "action", "entitlement_key", "reason", "user__email", "organization__slug")


@admin.register(ProductUsageEvent)
class ProductUsageEventAdmin(admin.ModelAdmin):
    list_display = ("product", "action", "quantity", "period_key", "user", "organization", "source", "created_at")
    list_filter = ("product", "action", "source")
    search_fields = ("product", "action", "period_key", "idempotency_key", "user__email", "organization__slug")
    readonly_fields = ("created_at",)


@admin.register(ProductAccessDecision)
class ProductAccessDecisionAdmin(admin.ModelAdmin):
    list_display = ("product", "action", "allowed", "reason", "user", "organization", "remaining", "created_at")
    list_filter = ("product", "action", "allowed", "reason")
    search_fields = ("product", "action", "reason", "user__email", "organization__slug")
    readonly_fields = ("created_at",)
