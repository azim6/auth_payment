from django.contrib import admin

from .models import (
    DeprovisioningPolicy,
    DirectoryGroup,
    DirectoryGroupMember,
    DirectoryUser,
    ScimApplication,
    ScimProvisioningEvent,
    ScimSyncJob,
)


@admin.register(ScimApplication)
class ScimApplicationAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "provider", "status", "token_prefix", "last_used_at", "created_at")
    list_filter = ("status", "provider", "allow_group_sync", "require_verified_domain")
    search_fields = ("name", "slug", "organization__slug", "token_prefix")
    readonly_fields = ("token_hash", "token_prefix", "last_used_at", "activated_at", "revoked_at", "created_at", "updated_at")


@admin.register(DirectoryUser)
class DirectoryUserAdmin(admin.ModelAdmin):
    list_display = ("email", "organization", "status", "active", "external_id", "last_synced_at")
    list_filter = ("status", "active", "organization")
    search_fields = ("email", "user_name", "external_id", "display_name")
    readonly_fields = ("created_at", "updated_at", "last_synced_at", "deprovisioned_at")


@admin.register(DirectoryGroup)
class DirectoryGroupAdmin(admin.ModelAdmin):
    list_display = ("display_name", "organization", "status", "mapped_role", "external_id", "last_synced_at")
    list_filter = ("status", "mapped_role", "organization")
    search_fields = ("display_name", "external_id")


@admin.register(DirectoryGroupMember)
class DirectoryGroupMemberAdmin(admin.ModelAdmin):
    list_display = ("organization", "group", "directory_user", "external_user_id", "created_at")
    search_fields = ("external_user_id", "directory_user__email", "group__display_name")


@admin.register(DeprovisioningPolicy)
class DeprovisioningPolicyAdmin(admin.ModelAdmin):
    list_display = ("organization", "action", "grace_period_hours", "preserve_billing_owner", "require_approval_for_owners")
    list_filter = ("action", "notify_admins", "require_approval_for_owners")


@admin.register(ScimSyncJob)
class ScimSyncJobAdmin(admin.ModelAdmin):
    list_display = ("organization", "scim_application", "status", "mode", "dry_run", "created_at", "finished_at")
    list_filter = ("status", "mode", "dry_run")
    readonly_fields = ("created_at", "started_at", "finished_at")


@admin.register(ScimProvisioningEvent)
class ScimProvisioningEventAdmin(admin.ModelAdmin):
    list_display = ("event_type", "result", "organization", "scim_application", "external_id", "created_at")
    list_filter = ("event_type", "result")
    search_fields = ("external_id", "message", "organization__slug")
    readonly_fields = ("created_at",)
