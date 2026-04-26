from rest_framework import serializers

from accounts.models import OAuthClient
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
from .services import generate_key_id


class OAuthClientField(serializers.SlugRelatedField):
    def __init__(self, **kwargs):
        super().__init__(slug_field="client_id", queryset=OAuthClient.objects.all(), **kwargs)


class OidcSigningKeySerializer(serializers.ModelSerializer):
    created_by_email = serializers.EmailField(source="created_by.email", read_only=True)

    class Meta:
        model = OidcSigningKey
        fields = [
            "id",
            "kid",
            "algorithm",
            "status",
            "public_jwk",
            "private_key_reference",
            "not_before",
            "not_after",
            "activated_at",
            "retiring_at",
            "retired_at",
            "revoked_at",
            "created_by_email",
            "rotation_note",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["status", "activated_at", "retiring_at", "retired_at", "revoked_at", "created_by_email", "created_at", "updated_at"]
        extra_kwargs = {"private_key_reference": {"write_only": True, "required": False}}

    def create(self, validated_data):
        validated_data.setdefault("kid", generate_key_id())
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)


class OAuthScopeDefinitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = OAuthScopeDefinition
        fields = [
            "id",
            "name",
            "display_name",
            "description",
            "sensitivity",
            "requires_consent",
            "staff_approval_required",
            "default_for_first_party",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def validate_name(self, value):
        cleaned = value.strip().lower()
        if " " in cleaned:
            raise serializers.ValidationError("Scopes must not contain spaces.")
        return cleaned


class OAuthClaimMappingSerializer(serializers.ModelSerializer):
    scope_name = serializers.SlugRelatedField(source="scope", slug_field="name", queryset=OAuthScopeDefinition.objects.all())

    class Meta:
        model = OAuthClaimMapping
        fields = ["id", "scope_name", "claim_name", "source_path", "token_type", "include_when_empty", "is_active", "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]


class OAuthClientTrustProfileSerializer(serializers.ModelSerializer):
    client_id = OAuthClientField(source="client")
    reviewed_by_email = serializers.EmailField(source="reviewed_by.email", read_only=True)

    class Meta:
        model = OAuthClientTrustProfile
        fields = [
            "id",
            "client_id",
            "trust_level",
            "requires_pkce",
            "requires_consent_screen",
            "allow_offline_access",
            "allow_refresh_token_rotation",
            "allow_dynamic_scopes",
            "max_access_token_lifetime_seconds",
            "max_refresh_token_lifetime_seconds",
            "allowed_claims",
            "risk_notes",
            "reviewed_by_email",
            "reviewed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["reviewed_by_email", "reviewed_at", "created_at", "updated_at"]


class OidcRefreshTokenPolicySerializer(serializers.ModelSerializer):
    client_id = OAuthClientField(source="client")

    class Meta:
        model = OidcRefreshTokenPolicy
        fields = [
            "id",
            "client_id",
            "rotate_on_use",
            "reuse_detection_enabled",
            "revoke_family_on_reuse",
            "idle_timeout_seconds",
            "absolute_lifetime_seconds",
            "sender_constrained_required",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class OAuthConsentGrantSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    client_id = OAuthClientField(source="client")

    class Meta:
        model = OAuthConsentGrant
        fields = [
            "id",
            "user",
            "user_email",
            "client_id",
            "scopes",
            "claims",
            "status",
            "consented_at",
            "expires_at",
            "revoked_at",
            "ip_address",
            "user_agent",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["status", "consented_at", "revoked_at", "ip_address", "user_agent", "created_at", "updated_at"]

    def create(self, validated_data):
        request = self.context.get("request")
        if request:
            validated_data["ip_address"] = request.META.get("REMOTE_ADDR")
            validated_data["user_agent"] = request.META.get("HTTP_USER_AGENT", "")
        return super().create(validated_data)


class OidcTokenExchangePolicySerializer(serializers.ModelSerializer):
    client_id = OAuthClientField(source="client")

    class Meta:
        model = OidcTokenExchangePolicy
        fields = [
            "id",
            "client_id",
            "require_pkce_for_public_clients",
            "require_nonce_for_id_token",
            "allowed_grant_types",
            "allowed_response_types",
            "require_exact_redirect_uri",
            "reject_plain_pkce",
            "require_consent_for_new_scopes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def validate(self, attrs):
        attrs.setdefault("allowed_grant_types", ["authorization_code", "refresh_token"])
        attrs.setdefault("allowed_response_types", ["code"])
        return attrs


class OidcDiscoveryMetadataSnapshotSerializer(serializers.ModelSerializer):
    generated_by_email = serializers.EmailField(source="generated_by.email", read_only=True)

    class Meta:
        model = OidcDiscoveryMetadataSnapshot
        fields = [
            "id",
            "issuer",
            "authorization_endpoint",
            "token_endpoint",
            "jwks_uri",
            "userinfo_endpoint",
            "scopes_supported",
            "claims_supported",
            "response_types_supported",
            "grant_types_supported",
            "signing_alg_values_supported",
            "metadata",
            "generated_by_email",
            "created_at",
        ]
        read_only_fields = fields


class ConsentEvaluationSerializer(serializers.Serializer):
    client_id = serializers.SlugRelatedField(slug_field="client_id", queryset=OAuthClient.objects.all())
    scopes = serializers.ListField(child=serializers.CharField(), allow_empty=False)

    def validate_scopes(self, value):
        return sorted({scope.strip().lower() for scope in value if scope.strip()})
