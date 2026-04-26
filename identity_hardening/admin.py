from django.contrib import admin

from .models import AccountRecoveryPolicy, IdentityAssuranceEvent, PasskeyChallenge, PasskeyCredential, StepUpPolicy, StepUpSession, TrustedDevice


@admin.register(PasskeyCredential)
class PasskeyCredentialAdmin(admin.ModelAdmin):
    list_display = ["user", "label", "platform", "status", "credential_id_prefix", "last_used_at", "created_at"]
    list_filter = ["platform", "status", "backup_eligible", "backup_state", "created_at"]
    search_fields = ["user__email", "label", "credential_id_prefix", "aaguid"]
    readonly_fields = ["credential_id_hash", "created_at", "updated_at", "last_used_at", "revoked_at"]


@admin.register(PasskeyChallenge)
class PasskeyChallengeAdmin(admin.ModelAdmin):
    list_display = ["purpose", "user", "challenge_prefix", "rp_id", "expires_at", "consumed_at", "created_at"]
    list_filter = ["purpose", "rp_id", "created_at"]
    search_fields = ["user__email", "challenge_prefix", "rp_id"]
    readonly_fields = ["challenge_hash", "created_at", "consumed_at"]


@admin.register(TrustedDevice)
class TrustedDeviceAdmin(admin.ModelAdmin):
    list_display = ["user", "name", "platform", "trust_level", "status", "last_seen_at", "expires_at"]
    list_filter = ["platform", "trust_level", "status"]
    search_fields = ["user__email", "name", "device_prefix"]
    readonly_fields = ["device_hash", "created_at", "updated_at", "last_seen_at", "revoked_at"]


@admin.register(StepUpPolicy)
class StepUpPolicyAdmin(admin.ModelAdmin):
    list_display = ["name", "organization", "trigger", "required_method", "max_age_seconds", "is_enforced"]
    list_filter = ["trigger", "required_method", "is_enforced"]
    search_fields = ["name", "organization__name", "organization__slug"]


@admin.register(StepUpSession)
class StepUpSessionAdmin(admin.ModelAdmin):
    list_display = ["user", "organization", "trigger", "method", "expires_at", "revoked_at"]
    list_filter = ["method", "trigger", "created_at"]
    search_fields = ["user__email", "trigger"]


@admin.register(AccountRecoveryPolicy)
class AccountRecoveryPolicyAdmin(admin.ModelAdmin):
    list_display = ["user", "organization", "status", "require_operator_review", "cooldown_hours", "updated_at"]
    list_filter = ["status", "require_operator_review", "require_mfa_reset_delay"]
    search_fields = ["user__email", "organization__name", "recovery_contact_email"]


@admin.register(IdentityAssuranceEvent)
class IdentityAssuranceEventAdmin(admin.ModelAdmin):
    list_display = ["event_type", "result", "method", "user", "organization", "risk_score", "created_at"]
    list_filter = ["result", "method", "event_type", "created_at"]
    search_fields = ["user__email", "organization__slug", "event_type"]
    readonly_fields = ["created_at"]
