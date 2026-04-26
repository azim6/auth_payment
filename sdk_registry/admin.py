from django.contrib import admin

from .models import IntegrationGuide, SdkCompatibilityMatrix, SdkRelease, SdkTelemetryEvent


@admin.register(SdkRelease)
class SdkReleaseAdmin(admin.ModelAdmin):
    list_display = ("platform", "version", "status", "minimum_api_version", "published_at", "created_at")
    list_filter = ("platform", "status")
    search_fields = ("platform", "version", "release_notes")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(IntegrationGuide)
class IntegrationGuideAdmin(admin.ModelAdmin):
    list_display = ("title", "audience", "slug", "is_published", "updated_at")
    list_filter = ("audience", "is_published")
    search_fields = ("title", "slug", "summary", "content_markdown")
    prepopulated_fields = {"slug": ("title",)}


@admin.register(SdkCompatibilityMatrix)
class SdkCompatibilityMatrixAdmin(admin.ModelAdmin):
    list_display = ("sdk_platform", "sdk_version", "api_version", "supports_pkce", "supports_step_up", "supports_passkeys")
    list_filter = ("sdk_platform", "api_version", "supports_passkeys")
    search_fields = ("sdk_platform", "sdk_version", "notes")


@admin.register(SdkTelemetryEvent)
class SdkTelemetryEventAdmin(admin.ModelAdmin):
    list_display = ("platform", "sdk_version", "event_type", "application_id", "created_at")
    list_filter = ("platform", "event_type", "created_at")
    search_fields = ("application_id", "event_name", "user_agent")
    readonly_fields = ("id", "created_at")
