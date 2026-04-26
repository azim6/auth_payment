from django.contrib import admin

from .models import (
    DevicePushToken,
    NotificationDelivery,
    NotificationEvent,
    NotificationPreference,
    NotificationProvider,
    NotificationSuppression,
    NotificationTemplate,
)


@admin.register(NotificationProvider)
class NotificationProviderAdmin(admin.ModelAdmin):
    list_display = ("name", "channel", "provider_code", "status", "priority", "last_success_at", "last_failure_at")
    list_filter = ("channel", "status", "provider_code")
    search_fields = ("name", "provider_code")


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ("key", "channel", "locale", "version", "organization", "project", "is_active")
    list_filter = ("channel", "locale", "is_active")
    search_fields = ("key", "subject_template", "body_template")


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ("user", "organization", "topic", "channel", "enabled", "locale")
    list_filter = ("channel", "topic", "enabled", "locale")
    search_fields = ("user__email", "topic")


@admin.register(DevicePushToken)
class DevicePushTokenAdmin(admin.ModelAdmin):
    list_display = ("user", "organization", "platform", "token_prefix", "is_active", "last_used_at", "revoked_at")
    list_filter = ("platform", "is_active")
    search_fields = ("user__email", "device_id", "token_prefix")
    readonly_fields = ("token_hash",)


@admin.register(NotificationEvent)
class NotificationEventAdmin(admin.ModelAdmin):
    list_display = ("event_type", "topic", "priority", "status", "organization", "user", "scheduled_for", "created_at")
    list_filter = ("topic", "priority", "status", "event_type")
    search_fields = ("event_type", "idempotency_key", "user__email", "organization__slug")


@admin.register(NotificationDelivery)
class NotificationDeliveryAdmin(admin.ModelAdmin):
    list_display = ("event", "channel", "recipient_hash", "status", "attempt_count", "next_attempt_at", "sent_at")
    list_filter = ("channel", "status")
    search_fields = ("recipient_hash", "provider_message_id", "event__event_type")
    readonly_fields = ("recipient_hash",)


@admin.register(NotificationSuppression)
class NotificationSuppressionAdmin(admin.ModelAdmin):
    list_display = ("channel", "recipient_hash", "reason", "expires_at", "created_by", "created_at")
    list_filter = ("channel", "reason")
    search_fields = ("recipient_hash", "note")
