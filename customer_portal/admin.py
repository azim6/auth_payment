from django.contrib import admin

from .models import PortalActivityLog, PortalApiKey, PortalOrganizationBookmark, PortalProfileSettings, PortalSupportRequest


@admin.register(PortalProfileSettings)
class PortalProfileSettingsAdmin(admin.ModelAdmin):
    list_display = ("user", "preferred_locale", "timezone", "theme", "marketing_opt_in", "updated_at")
    search_fields = ("user__email", "display_name")
    readonly_fields = ("created_at", "updated_at")


@admin.register(PortalOrganizationBookmark)
class PortalOrganizationBookmarkAdmin(admin.ModelAdmin):
    list_display = ("user", "organization", "label", "sort_order", "created_at")
    search_fields = ("user__email", "organization__slug", "organization__name")
    list_filter = ("created_at",)


@admin.register(PortalApiKey)
class PortalApiKeyAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "organization", "key_prefix", "status", "last_used_at", "expires_at", "created_at")
    search_fields = ("name", "user__email", "organization__slug", "key_prefix")
    list_filter = ("status", "created_at", "expires_at")
    readonly_fields = ("key_hash", "key_prefix", "last_used_at", "revoked_at", "created_at", "updated_at")


@admin.register(PortalSupportRequest)
class PortalSupportRequestAdmin(admin.ModelAdmin):
    list_display = ("subject", "user", "organization", "category", "status", "priority", "created_at")
    search_fields = ("subject", "message", "user__email", "organization__slug")
    list_filter = ("category", "status", "priority", "created_at")
    readonly_fields = ("created_at", "updated_at", "resolved_at")


@admin.register(PortalActivityLog)
class PortalActivityLogAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "organization", "domain", "event_type", "ip_address", "created_at")
    search_fields = ("title", "summary", "user__email", "organization__slug", "event_type")
    list_filter = ("domain", "event_type", "created_at")
    readonly_fields = ("created_at",)
