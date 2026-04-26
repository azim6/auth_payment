from django.contrib import admin

from .models import (
    AdminNote,
    AdminWorkspacePreference,
    BulkActionRequest,
    DashboardSnapshot,
    DashboardWidget,
    OperatorTask,
    SavedAdminView,
)


@admin.register(DashboardWidget)
class DashboardWidgetAdmin(admin.ModelAdmin):
    list_display = ("key", "title", "domain", "widget_type", "enabled", "sort_order")
    list_filter = ("domain", "widget_type", "enabled")
    search_fields = ("key", "title", "description", "permission_code")


@admin.register(SavedAdminView)
class SavedAdminViewAdmin(admin.ModelAdmin):
    list_display = ("name", "resource", "visibility", "owner", "is_default")
    list_filter = ("resource", "visibility", "is_default")
    search_fields = ("name", "resource", "owner__email")


@admin.register(OperatorTask)
class OperatorTaskAdmin(admin.ModelAdmin):
    list_display = ("title", "domain", "priority", "status", "assigned_to", "organization", "due_at")
    list_filter = ("domain", "priority", "status")
    search_fields = ("title", "description", "assigned_to__email", "organization__name", "organization__slug")
    date_hierarchy = "created_at"


@admin.register(BulkActionRequest)
class BulkActionRequestAdmin(admin.ModelAdmin):
    list_display = ("action", "status", "estimated_count", "processed_count", "failed_count", "requested_by", "approved_by", "created_at")
    list_filter = ("action", "status")
    search_fields = ("reason", "requested_by__email", "approved_by__email", "idempotency_key")
    date_hierarchy = "created_at"


@admin.register(AdminNote)
class AdminNoteAdmin(admin.ModelAdmin):
    list_display = ("title", "subject_type", "subject_id", "visibility", "pinned", "author", "created_at")
    list_filter = ("visibility", "pinned", "subject_type")
    search_fields = ("title", "body", "subject_id", "author__email")


@admin.register(AdminWorkspacePreference)
class AdminWorkspacePreferenceAdmin(admin.ModelAdmin):
    list_display = ("user", "landing_page", "timezone_name", "updated_at")
    search_fields = ("user__email", "landing_page", "timezone_name")


@admin.register(DashboardSnapshot)
class DashboardSnapshotAdmin(admin.ModelAdmin):
    list_display = ("name", "generated_at", "generated_by")
    list_filter = ("name",)
    search_fields = ("name", "generated_by__email")
    date_hierarchy = "generated_at"
