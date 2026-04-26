from django.contrib import admin

from .models import AdminApprovalRequest, AuditExport, EvidencePack, PolicyDocument, UserPolicyAcceptance


@admin.register(PolicyDocument)
class PolicyDocumentAdmin(admin.ModelAdmin):
    list_display = ("policy_type", "version", "title", "is_active", "published_at", "retired_at")
    list_filter = ("policy_type", "is_active", "requires_user_acceptance", "requires_admin_acceptance")
    search_fields = ("title", "version", "checksum_sha256")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(UserPolicyAcceptance)
class UserPolicyAcceptanceAdmin(admin.ModelAdmin):
    list_display = ("user", "organization", "policy", "accepted_at", "ip_address")
    list_filter = ("policy__policy_type", "accepted_at")
    search_fields = ("user__email", "organization__slug", "policy__version")
    readonly_fields = ("id", "accepted_at")


@admin.register(AdminApprovalRequest)
class AdminApprovalRequestAdmin(admin.ModelAdmin):
    list_display = ("action_type", "status", "requested_by", "reviewed_by", "organization", "created_at")
    list_filter = ("action_type", "status", "created_at")
    search_fields = ("summary", "requested_by__email", "reviewed_by__email", "organization__slug")
    readonly_fields = ("id", "reviewed_at", "created_at", "updated_at")


@admin.register(AuditExport)
class AuditExportAdmin(admin.ModelAdmin):
    list_display = ("export_type", "status", "requested_by", "organization", "record_count", "created_at")
    list_filter = ("export_type", "status", "created_at")
    search_fields = ("requested_by__email", "organization__slug", "checksum_sha256", "storage_uri")
    readonly_fields = ("id", "created_at", "completed_at")


@admin.register(EvidencePack)
class EvidencePackAdmin(admin.ModelAdmin):
    list_display = ("pack_type", "status", "title", "organization", "subject_user", "created_at")
    list_filter = ("pack_type", "status", "created_at")
    search_fields = ("title", "organization__slug", "subject_user__email")
    readonly_fields = ("id", "locked_at", "created_at", "updated_at")
