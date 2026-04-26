from django.contrib import admin

from .models import FeatureFlagInventory, VerificationSnapshot


@admin.register(VerificationSnapshot)
class VerificationSnapshotAdmin(admin.ModelAdmin):
    list_display = ("id", "status", "created_by", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("status",)
    readonly_fields = ("summary", "checks", "created_at")


@admin.register(FeatureFlagInventory)
class FeatureFlagInventoryAdmin(admin.ModelAdmin):
    list_display = ("app_label", "tier", "enabled_by_default", "updated_at")
    list_filter = ("tier", "enabled_by_default")
    search_fields = ("app_label",)
