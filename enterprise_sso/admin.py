from django.contrib import admin

from .models import EnterpriseIdentityProvider, JitProvisioningRule, SsoLoginEvent, SsoPolicy, VerifiedDomain


@admin.register(EnterpriseIdentityProvider)
class EnterpriseIdentityProviderAdmin(admin.ModelAdmin):
    list_display = ["organization", "name", "slug", "protocol", "status", "last_tested_at", "activated_at", "created_at"]
    list_filter = ["protocol", "status", "require_signed_assertions", "require_encrypted_assertions"]
    search_fields = ["organization__slug", "organization__name", "name", "slug", "entity_id", "oidc_issuer"]
    readonly_fields = ["created_at", "updated_at", "last_tested_at", "activated_at"]


@admin.register(VerifiedDomain)
class VerifiedDomainAdmin(admin.ModelAdmin):
    list_display = ["domain", "organization", "method", "status", "verified_at", "last_checked_at"]
    list_filter = ["method", "status"]
    search_fields = ["domain", "organization__slug", "organization__name"]
    readonly_fields = ["verification_token_hash", "verified_at", "last_checked_at", "created_at", "updated_at"]


@admin.register(SsoPolicy)
class SsoPolicyAdmin(admin.ModelAdmin):
    list_display = ["organization", "enforcement", "default_identity_provider", "allow_jit_provisioning", "require_mfa_after_sso", "updated_at"]
    list_filter = ["enforcement", "allow_jit_provisioning", "require_verified_domain_for_jit", "require_mfa_after_sso"]
    search_fields = ["organization__slug", "organization__name"]


@admin.register(JitProvisioningRule)
class JitProvisioningRuleAdmin(admin.ModelAdmin):
    list_display = ["organization", "identity_provider", "name", "priority", "status", "claim", "operator", "assigned_role"]
    list_filter = ["status", "assigned_role", "operator"]
    search_fields = ["organization__slug", "identity_provider__name", "name", "claim", "value"]


@admin.register(SsoLoginEvent)
class SsoLoginEventAdmin(admin.ModelAdmin):
    list_display = ["email", "organization", "identity_provider", "result", "reason", "created_at"]
    list_filter = ["result", "created_at"]
    search_fields = ["email", "subject", "organization__slug", "identity_provider__name", "reason"]
    readonly_fields = ["created_at"]
