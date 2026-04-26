from django.contrib import admin

from .models import (
    OAuthClaimMapping,
    OAuthClientTrustProfile,
    OAuthConsentGrant,
    OAuthScopeDefinition,
    OidcDiscoveryMetadataSnapshot,
    OidcRefreshTokenPolicy,
    OidcSigningKey,
    OidcTokenExchangePolicy,
)


@admin.register(OidcSigningKey)
class OidcSigningKeyAdmin(admin.ModelAdmin):
    list_display = ("kid", "algorithm", "status", "not_before", "not_after", "activated_at", "created_at")
    list_filter = ("algorithm", "status")
    search_fields = ("kid", "private_key_reference")
    readonly_fields = ("id", "activated_at", "retiring_at", "retired_at", "revoked_at", "created_at", "updated_at")


@admin.register(OAuthScopeDefinition)
class OAuthScopeDefinitionAdmin(admin.ModelAdmin):
    list_display = ("name", "display_name", "sensitivity", "requires_consent", "staff_approval_required", "is_active")
    list_filter = ("sensitivity", "requires_consent", "staff_approval_required", "is_active")
    search_fields = ("name", "display_name")


@admin.register(OAuthClaimMapping)
class OAuthClaimMappingAdmin(admin.ModelAdmin):
    list_display = ("scope", "claim_name", "source_path", "token_type", "is_active")
    list_filter = ("token_type", "is_active")
    search_fields = ("claim_name", "source_path", "scope__name")


@admin.register(OAuthClientTrustProfile)
class OAuthClientTrustProfileAdmin(admin.ModelAdmin):
    list_display = ("client", "trust_level", "requires_pkce", "requires_consent_screen", "allow_offline_access", "reviewed_at")
    list_filter = ("trust_level", "requires_pkce", "requires_consent_screen", "allow_offline_access")
    search_fields = ("client__name", "client__client_id")
    readonly_fields = ("created_at", "updated_at", "reviewed_at")


@admin.register(OidcRefreshTokenPolicy)
class OidcRefreshTokenPolicyAdmin(admin.ModelAdmin):
    list_display = ("client", "rotate_on_use", "reuse_detection_enabled", "revoke_family_on_reuse", "sender_constrained_required")
    list_filter = ("rotate_on_use", "reuse_detection_enabled", "revoke_family_on_reuse", "sender_constrained_required")
    search_fields = ("client__name", "client__client_id")


@admin.register(OAuthConsentGrant)
class OAuthConsentGrantAdmin(admin.ModelAdmin):
    list_display = ("user", "client", "status", "consented_at", "expires_at", "revoked_at")
    list_filter = ("status", "client")
    search_fields = ("user__email", "client__client_id", "client__name")
    readonly_fields = ("consented_at", "created_at", "updated_at")


@admin.register(OidcTokenExchangePolicy)
class OidcTokenExchangePolicyAdmin(admin.ModelAdmin):
    list_display = ("client", "require_pkce_for_public_clients", "require_nonce_for_id_token", "require_exact_redirect_uri", "reject_plain_pkce")
    list_filter = ("require_pkce_for_public_clients", "require_nonce_for_id_token", "require_exact_redirect_uri", "reject_plain_pkce")
    search_fields = ("client__name", "client__client_id")


@admin.register(OidcDiscoveryMetadataSnapshot)
class OidcDiscoveryMetadataSnapshotAdmin(admin.ModelAdmin):
    list_display = ("issuer", "created_at", "generated_by")
    search_fields = ("issuer",)
    readonly_fields = ("created_at",)
