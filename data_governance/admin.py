from django.contrib import admin

from .models import (
    AnonymizationRecord,
    DataAsset,
    DataCategory,
    DataInventorySnapshot,
    DataSubjectRequest,
    LegalHold,
    RetentionJob,
    RetentionPolicy,
)


@admin.register(DataCategory)
class DataCategoryAdmin(admin.ModelAdmin):
    list_display = ["key", "name", "sensitivity", "processing_basis", "is_pii", "default_retention_days", "status"]
    list_filter = ["sensitivity", "processing_basis", "is_pii", "is_payment_data", "status"]
    search_fields = ["key", "name", "description", "owner_team"]


@admin.register(DataAsset)
class DataAssetAdmin(admin.ModelAdmin):
    list_display = ["key", "asset_type", "app_label", "model_name", "contains_pii", "contains_payment_data", "status"]
    list_filter = ["asset_type", "app_label", "contains_pii", "contains_payment_data", "encryption_required", "status"]
    search_fields = ["key", "name", "app_label", "model_name", "storage_location"]
    filter_horizontal = ["categories"]


@admin.register(RetentionPolicy)
class RetentionPolicyAdmin(admin.ModelAdmin):
    list_display = ["key", "name", "retention_days", "action", "grace_days", "is_active", "owner_team"]
    list_filter = ["action", "is_active", "legal_hold_exempt"]
    search_fields = ["key", "name", "description", "owner_team"]
    filter_horizontal = ["assets", "categories"]


@admin.register(LegalHold)
class LegalHoldAdmin(admin.ModelAdmin):
    list_display = ["scope", "reason", "status", "user", "organization", "category", "starts_at", "ends_at"]
    list_filter = ["scope", "status"]
    search_fields = ["reason", "description", "user__email", "organization__slug", "category__key"]


@admin.register(DataSubjectRequest)
class DataSubjectRequestAdmin(admin.ModelAdmin):
    list_display = ["request_type", "status", "user", "organization", "due_at", "created_at", "completed_at"]
    list_filter = ["request_type", "status"]
    search_fields = ["user__email", "organization__slug", "rejection_reason", "evidence_checksum"]


@admin.register(RetentionJob)
class RetentionJobAdmin(admin.ModelAdmin):
    list_display = ["policy", "status", "dry_run", "candidate_count", "processed_count", "blocked_count", "cutoff_at"]
    list_filter = ["status", "dry_run"]
    search_fields = ["policy__key", "error_message"]


@admin.register(AnonymizationRecord)
class AnonymizationRecordAdmin(admin.ModelAdmin):
    list_display = ["asset", "subject_type", "action", "performed_at"]
    list_filter = ["action", "subject_type"]
    search_fields = ["subject_id_hash", "asset__key"]
    readonly_fields = ["id", "performed_at"]


@admin.register(DataInventorySnapshot)
class DataInventorySnapshotAdmin(admin.ModelAdmin):
    list_display = ["generated_at", "asset_count", "pii_asset_count", "restricted_asset_count", "active_policy_count", "active_legal_hold_count"]
    readonly_fields = ["id", "generated_at"]
