from django.contrib import admin

from .models import BackupSnapshot, EnvironmentCheck, MaintenanceWindow, ReleaseRecord, RestoreRun, ServiceHealthCheck, StatusIncident


@admin.register(EnvironmentCheck)
class EnvironmentCheckAdmin(admin.ModelAdmin):
    list_display = ("key", "status", "checked_at")
    list_filter = ("status",)
    search_fields = ("key", "message")
    readonly_fields = ("checked_at",)


@admin.register(ServiceHealthCheck)
class ServiceHealthCheckAdmin(admin.ModelAdmin):
    list_display = ("name", "status", "latency_ms", "checked_at")
    list_filter = ("status",)
    search_fields = ("name", "message")


@admin.register(MaintenanceWindow)
class MaintenanceWindowAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "starts_at", "ends_at", "created_by")
    list_filter = ("status", "starts_at")
    search_fields = ("title", "customer_message", "internal_notes")


@admin.register(BackupSnapshot)
class BackupSnapshotAdmin(admin.ModelAdmin):
    list_display = ("label", "status", "database_name", "size_bytes", "created_at")
    list_filter = ("status", "database_name")
    search_fields = ("label", "storage_uri", "checksum_sha256")


@admin.register(RestoreRun)
class RestoreRunAdmin(admin.ModelAdmin):
    list_display = ("backup", "status", "target_environment", "requested_by", "approved_by", "created_at")
    list_filter = ("status", "target_environment")
    search_fields = ("reason", "result_notes")


@admin.register(StatusIncident)
class StatusIncidentAdmin(admin.ModelAdmin):
    list_display = ("title", "state", "impact", "started_at", "resolved_at")
    list_filter = ("state", "impact")
    search_fields = ("title", "public_message", "internal_notes")


@admin.register(ReleaseRecord)
class ReleaseRecordAdmin(admin.ModelAdmin):
    list_display = ("version", "status", "git_sha", "image_tag", "deployed_at")
    list_filter = ("status",)
    search_fields = ("version", "git_sha", "image_tag", "changelog")
