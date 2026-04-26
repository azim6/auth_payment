from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import AccountToken, User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    ordering = ("email",)
    list_display = ("email", "username", "display_name", "email_verified", "is_staff", "is_active")
    search_fields = ("email", "username", "display_name")
    readonly_fields = ("id", "created_at", "updated_at", "last_login")

    fieldsets = (
        (None, {"fields": ("id", "email", "username", "password")}),
        (_("Profile"), {"fields": ("display_name", "avatar_url", "bio")}),
        (_("Verification"), {"fields": ("email_verified",)}),
        (_("Permissions"), {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        (_("Important dates"), {"fields": ("last_login", "last_seen_at", "created_at", "updated_at")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "username", "password1", "password2", "is_staff", "is_superuser", "is_active"),
        }),
    )


@admin.register(AccountToken)
class AccountTokenAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "purpose", "expires_at", "used_at", "created_at")
    list_filter = ("purpose", "used_at", "expires_at")
    search_fields = ("user__email", "user__username", "token_hash")
    readonly_fields = ("id", "user", "purpose", "token_hash", "expires_at", "used_at", "created_at")


from .models import MfaDevice, RecoveryCode


@admin.register(MfaDevice)
class MfaDeviceAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "type", "name", "confirmed_at", "last_used_at", "created_at")
    list_filter = ("type", "confirmed_at", "last_used_at")
    search_fields = ("user__email", "user__username", "name")
    readonly_fields = ("id", "user", "type", "name", "secret", "confirmed_at", "last_used_at", "created_at", "updated_at")


@admin.register(RecoveryCode)
class RecoveryCodeAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "used_at", "created_at")
    list_filter = ("used_at", "created_at")
    search_fields = ("user__email", "user__username")
    readonly_fields = ("id", "user", "code_hash", "used_at", "created_at")

from .models import AuthorizationCode, OAuthClient


@admin.register(OAuthClient)
class OAuthClientAdmin(admin.ModelAdmin):
    list_display = ("name", "client_id", "is_confidential", "is_active", "created_at")
    list_filter = ("is_confidential", "is_active", "created_at")
    search_fields = ("name", "client_id", "owner__email")
    readonly_fields = ("id", "client_id", "client_secret_hash", "created_at", "updated_at")


@admin.register(AuthorizationCode)
class AuthorizationCodeAdmin(admin.ModelAdmin):
    list_display = ("id", "client", "user", "expires_at", "used_at", "created_at")
    list_filter = ("expires_at", "used_at", "created_at")
    search_fields = ("client__client_id", "client__name", "user__email")
    readonly_fields = ("id", "client", "user", "code_hash", "redirect_uri", "scope", "state", "nonce", "code_challenge", "code_challenge_method", "expires_at", "used_at", "created_at")

from .models import AuditLog, OAuthTokenActivity, ServiceCredential


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "category", "action", "outcome", "actor", "client_id", "ip_address")
    list_filter = ("category", "action", "outcome", "created_at")
    search_fields = ("actor__email", "client_id", "request_id", "user_agent")
    readonly_fields = (
        "id", "actor", "category", "action", "outcome", "ip_address", "user_agent",
        "request_id", "client_id", "subject_user_id", "metadata", "created_at",
    )


@admin.register(ServiceCredential)
class ServiceCredentialAdmin(admin.ModelAdmin):
    list_display = ("name", "key_prefix", "is_active", "last_used_at", "expires_at", "created_at")
    list_filter = ("is_active", "last_used_at", "expires_at", "created_at")
    search_fields = ("name", "key_prefix", "owner__email")
    readonly_fields = ("id", "owner", "key_prefix", "key_hash", "last_used_at", "created_at", "updated_at")


@admin.register(OAuthTokenActivity)
class OAuthTokenActivityAdmin(admin.ModelAdmin):
    list_display = ("created_at", "token_type", "user", "client", "service_credential", "expires_at", "revoked_at")
    list_filter = ("token_type", "expires_at", "revoked_at", "created_at")
    search_fields = ("jti", "user__email", "client__client_id", "service_credential__name")
    readonly_fields = (
        "id", "jti", "token_type", "user", "client", "service_credential", "scope",
        "expires_at", "revoked_at", "created_at", "last_seen_at", "metadata",
    )


from .models import AuthSessionDevice, RefreshTokenFamily


@admin.register(AuthSessionDevice)
class AuthSessionDeviceAdmin(admin.ModelAdmin):
    list_display = ("user", "label", "ip_address", "last_seen_at", "revoked_at", "created_at")
    list_filter = ("revoked_at", "last_seen_at", "created_at")
    search_fields = ("user__email", "label", "ip_address", "user_agent")
    readonly_fields = ("id", "user", "session_key_hash", "label", "user_agent", "ip_address", "last_seen_at", "revoked_at", "created_at", "updated_at")


@admin.register(RefreshTokenFamily)
class RefreshTokenFamilyAdmin(admin.ModelAdmin):
    list_display = ("user", "client_id", "jti", "expires_at", "revoked_at", "created_at")
    list_filter = ("client_id", "expires_at", "revoked_at", "created_at")
    search_fields = ("user__email", "jti", "client_id", "ip_address", "user_agent")
    readonly_fields = ("id", "user", "jti", "parent_jti", "client_id", "user_agent", "ip_address", "expires_at", "revoked_at", "created_at", "last_seen_at", "metadata")


from .models import AccountDeletionRequest, DataExportRequest, PrivacyPreference, UserConsent


@admin.register(PrivacyPreference)
class PrivacyPreferenceAdmin(admin.ModelAdmin):
    list_display = ("user", "analytics_consent", "marketing_email_consent", "product_email_consent", "profile_discoverable", "updated_at")
    list_filter = ("analytics_consent", "marketing_email_consent", "product_email_consent", "profile_discoverable", "data_processing_region")
    search_fields = ("user__email", "user__username")
    readonly_fields = ("created_at", "updated_at")


@admin.register(UserConsent)
class UserConsentAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "consent_type", "version", "granted", "source")
    list_filter = ("consent_type", "version", "granted", "source", "created_at")
    search_fields = ("user__email", "user__username", "version", "user_agent")
    readonly_fields = ("id", "user", "consent_type", "version", "granted", "source", "ip_address", "user_agent", "metadata", "created_at")


@admin.register(DataExportRequest)
class DataExportRequestAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "status", "format", "expires_at", "completed_at")
    list_filter = ("status", "format", "expires_at", "created_at")
    search_fields = ("user__email", "user__username", "download_url", "error")
    readonly_fields = ("id", "user", "status", "format", "download_url", "expires_at", "error", "requested_ip", "requested_user_agent", "completed_at", "created_at", "updated_at")


@admin.register(AccountDeletionRequest)
class AccountDeletionRequestAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "status", "scheduled_for", "confirmed_at", "cancelled_at", "completed_at")
    list_filter = ("status", "scheduled_for", "created_at")
    search_fields = ("user__email", "user__username", "reason")
    readonly_fields = ("id", "user", "status", "reason", "requested_ip", "requested_user_agent", "confirm_before", "scheduled_for", "confirmed_at", "cancelled_at", "completed_at", "created_at", "updated_at")


from .models import Organization, OrganizationInvitation, OrganizationMembership, TenantServiceCredential


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "owner", "plan", "is_active", "created_at")
    list_filter = ("plan", "is_active", "created_at")
    search_fields = ("name", "slug", "owner__email")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(OrganizationMembership)
class OrganizationMembershipAdmin(admin.ModelAdmin):
    list_display = ("organization", "user", "role", "is_active", "joined_at")
    list_filter = ("role", "is_active", "joined_at")
    search_fields = ("organization__name", "organization__slug", "user__email")
    readonly_fields = ("id", "joined_at", "updated_at")


@admin.register(OrganizationInvitation)
class OrganizationInvitationAdmin(admin.ModelAdmin):
    list_display = ("organization", "email", "role", "expires_at", "accepted_at", "revoked_at", "created_at")
    list_filter = ("role", "expires_at", "accepted_at", "revoked_at", "created_at")
    search_fields = ("organization__name", "organization__slug", "email", "invited_by__email")
    readonly_fields = ("id", "organization", "email", "role", "token_hash", "invited_by", "expires_at", "accepted_at", "revoked_at", "created_at")


@admin.register(TenantServiceCredential)
class TenantServiceCredentialAdmin(admin.ModelAdmin):
    list_display = ("organization", "name", "key_prefix", "is_active", "last_used_at", "expires_at", "created_at")
    list_filter = ("is_active", "last_used_at", "expires_at", "created_at")
    search_fields = ("organization__name", "organization__slug", "name", "key_prefix", "created_by__email")
    readonly_fields = ("id", "organization", "created_by", "key_prefix", "key_hash", "last_used_at", "created_at", "updated_at")

from .models import PermissionPolicy, RolePermissionGrant


@admin.register(PermissionPolicy)
class PermissionPolicyAdmin(admin.ModelAdmin):
    list_display = ("organization", "code", "name", "is_active", "expires_at", "created_at")
    list_filter = ("is_active", "expires_at", "created_at")
    search_fields = ("organization__name", "organization__slug", "code", "name")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(RolePermissionGrant)
class RolePermissionGrantAdmin(admin.ModelAdmin):
    list_display = ("organization", "role", "policy", "effect", "created_at")
    list_filter = ("role", "effect", "created_at")
    search_fields = ("organization__name", "organization__slug", "policy__code", "policy__name")
    readonly_fields = ("id", "created_at", "updated_at")

