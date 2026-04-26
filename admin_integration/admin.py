from django.contrib import admin

from .models import AdminApiContractEndpoint, AdminApiScope, AdminIntegrationReadinessSnapshot, AdminRequestAudit, AdminServiceCredential


@admin.register(AdminServiceCredential)
class AdminServiceCredentialAdmin(admin.ModelAdmin):
    list_display = ["name", "key_prefix", "signing_key_id", "is_active", "last_used_at", "expires_at", "created_at"]
    list_filter = ["is_active", "created_at", "expires_at"]
    search_fields = ["name", "key_prefix", "signing_key_id"]
    readonly_fields = ["key_hash", "last_used_at", "rotated_at", "created_at", "updated_at"]


@admin.register(AdminApiScope)
class AdminApiScopeAdmin(admin.ModelAdmin):
    list_display = ["code", "risk", "requires_two_person_approval", "enabled"]
    list_filter = ["risk", "requires_two_person_approval", "enabled"]
    search_fields = ["code", "title"]


@admin.register(AdminApiContractEndpoint)
class AdminApiContractEndpointAdmin(admin.ModelAdmin):
    list_display = ["method", "path", "domain", "required_scope", "stable", "enabled"]
    list_filter = ["domain", "method", "stable", "enabled"]
    search_fields = ["path", "required_scope", "description"]


@admin.register(AdminRequestAudit)
class AdminRequestAuditAdmin(admin.ModelAdmin):
    list_display = ["method", "path", "decision", "status_code", "ip_address", "created_at"]
    list_filter = ["decision", "status_code", "created_at"]
    search_fields = ["path", "key_prefix", "error"]
    readonly_fields = [field.name for field in AdminRequestAudit._meta.fields]


@admin.register(AdminIntegrationReadinessSnapshot)
class AdminIntegrationReadinessSnapshotAdmin(admin.ModelAdmin):
    list_display = ["status", "created_by", "created_at"]
    list_filter = ["status", "created_at"]
    readonly_fields = ["status", "checks", "metadata", "created_by", "created_at"]
