from django.contrib import admin

from .models import DeveloperApplication, IntegrationAuditEvent, SDKTokenPolicy, WebhookDelivery, WebhookSubscription


@admin.register(DeveloperApplication)
class DeveloperApplicationAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "project", "app_type", "environment", "status", "client_id", "last_used_at")
    list_filter = ("app_type", "environment", "status", "require_pkce", "require_mfa")
    search_fields = ("name", "slug", "client_id", "organization__slug", "project__code")
    readonly_fields = ("id", "client_id", "client_secret_prefix", "created_at", "updated_at", "last_used_at")


@admin.register(SDKTokenPolicy)
class SDKTokenPolicyAdmin(admin.ModelAdmin):
    list_display = ("application", "platform", "allow_public_client", "require_device_binding", "require_attestation", "max_token_ttl_seconds")
    list_filter = ("platform", "allow_public_client", "require_device_binding", "require_attestation")
    search_fields = ("application__name", "application__client_id")


@admin.register(WebhookSubscription)
class WebhookSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "application", "status", "target_url", "last_success_at", "last_failure_at")
    list_filter = ("status",)
    search_fields = ("name", "target_url", "organization__slug", "application__name")
    readonly_fields = ("id", "secret_prefix", "created_at", "updated_at", "last_success_at", "last_failure_at")


@admin.register(WebhookDelivery)
class WebhookDeliveryAdmin(admin.ModelAdmin):
    list_display = ("event_type", "subscription", "status", "attempt_count", "next_attempt_at", "delivered_at")
    list_filter = ("status", "event_type")
    search_fields = ("event_type", "subscription__name", "subscription__organization__slug")
    readonly_fields = ("id", "event_id", "created_at", "updated_at")


@admin.register(IntegrationAuditEvent)
class IntegrationAuditEventAdmin(admin.ModelAdmin):
    list_display = ("organization", "action", "actor", "application", "created_at")
    list_filter = ("action",)
    search_fields = ("organization__slug", "action", "actor__email", "application__name")
    readonly_fields = ("id", "created_at")
