import hashlib
import secrets

from django.utils import timezone
from rest_framework import serializers

from accounts.models import Organization, OrganizationMembership
from .models import EnterpriseIdentityProvider, JitProvisioningRule, SsoLoginEvent, SsoPolicy, VerifiedDomain


MANAGE_ROLES = {OrganizationMembership.Role.OWNER, OrganizationMembership.Role.ADMIN}


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _domain_token():
    return secrets.token_urlsafe(32)


class OrganizationSlugField(serializers.SlugRelatedField):
    def __init__(self, **kwargs):
        super().__init__(slug_field="slug", queryset=Organization.objects.all(), **kwargs)


class EnterpriseIdentityProviderSerializer(serializers.ModelSerializer):
    organization = OrganizationSlugField()
    created_by_email = serializers.EmailField(source="created_by.email", read_only=True)

    class Meta:
        model = EnterpriseIdentityProvider
        fields = [
            "id",
            "organization",
            "name",
            "slug",
            "protocol",
            "status",
            "entity_id",
            "sso_url",
            "slo_url",
            "x509_certificate_fingerprint",
            "x509_certificate_pem",
            "metadata_url",
            "metadata_xml",
            "oidc_issuer",
            "client_id",
            "default_role",
            "allowed_groups",
            "attribute_mapping",
            "require_signed_assertions",
            "require_encrypted_assertions",
            "allow_idp_initiated_login",
            "created_by_email",
            "last_tested_at",
            "activated_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["status", "created_by_email", "last_tested_at", "activated_at", "created_at", "updated_at"]
        extra_kwargs = {"x509_certificate_pem": {"write_only": True, "required": False}}

    def validate_default_role(self, value):
        allowed = {choice[0] for choice in OrganizationMembership.Role.choices}
        if value not in allowed:
            raise serializers.ValidationError("default_role must be one of the organization membership roles.")
        return value

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)


class VerifiedDomainSerializer(serializers.ModelSerializer):
    organization = OrganizationSlugField()
    verification_record = serializers.SerializerMethodField()
    raw_verification_token = serializers.CharField(read_only=True)

    class Meta:
        model = VerifiedDomain
        fields = [
            "id",
            "organization",
            "domain",
            "method",
            "status",
            "verification_token_prefix",
            "verification_record",
            "raw_verification_token",
            "verified_at",
            "last_checked_at",
            "failure_reason",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "status",
            "verification_token_prefix",
            "verification_record",
            "raw_verification_token",
            "verified_at",
            "last_checked_at",
            "failure_reason",
            "created_at",
            "updated_at",
        ]

    def get_verification_record(self, obj):
        return {
            "type": "TXT",
            "name": f"_auth-platform-sso.{obj.domain}",
            "value_prefix": obj.verification_token_prefix,
            "status": obj.status,
        }

    def create(self, validated_data):
        token = _domain_token()
        instance = VerifiedDomain.objects.create(
            **validated_data,
            verification_token_prefix=token[:16],
            verification_token_hash=_hash_token(token),
        )
        instance.raw_verification_token = token
        return instance


class SsoPolicySerializer(serializers.ModelSerializer):
    organization = OrganizationSlugField()
    default_identity_provider_id = serializers.PrimaryKeyRelatedField(
        source="default_identity_provider",
        queryset=EnterpriseIdentityProvider.objects.all(),
        allow_null=True,
        required=False,
    )
    updated_by_email = serializers.EmailField(source="updated_by.email", read_only=True)

    class Meta:
        model = SsoPolicy
        fields = [
            "id",
            "organization",
            "enforcement",
            "default_identity_provider_id",
            "allow_password_fallback_for_owners",
            "allow_jit_provisioning",
            "require_verified_domain_for_jit",
            "require_mfa_after_sso",
            "allowed_email_domains",
            "blocked_email_domains",
            "updated_by_email",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["updated_by_email", "created_at", "updated_at"]

    def validate(self, attrs):
        provider = attrs.get("default_identity_provider") or getattr(self.instance, "default_identity_provider", None)
        org = attrs.get("organization") or getattr(self.instance, "organization", None)
        if provider and org and provider.organization_id != org.id:
            raise serializers.ValidationError("default_identity_provider must belong to the same organization.")
        return attrs

    def create(self, validated_data):
        validated_data["updated_by"] = self.context["request"].user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data["updated_by"] = self.context["request"].user
        return super().update(instance, validated_data)


class JitProvisioningRuleSerializer(serializers.ModelSerializer):
    organization = OrganizationSlugField()
    identity_provider_id = serializers.PrimaryKeyRelatedField(source="identity_provider", queryset=EnterpriseIdentityProvider.objects.all())

    class Meta:
        model = JitProvisioningRule
        fields = [
            "id",
            "organization",
            "identity_provider_id",
            "name",
            "priority",
            "status",
            "claim",
            "operator",
            "value",
            "assigned_role",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def validate(self, attrs):
        provider = attrs.get("identity_provider") or getattr(self.instance, "identity_provider", None)
        org = attrs.get("organization") or getattr(self.instance, "organization", None)
        if provider and org and provider.organization_id != org.id:
            raise serializers.ValidationError("identity_provider must belong to the same organization.")
        role = attrs.get("assigned_role") or getattr(self.instance, "assigned_role", "member")
        if role not in {choice[0] for choice in OrganizationMembership.Role.choices}:
            raise serializers.ValidationError("assigned_role must be one of the organization membership roles.")
        return attrs


class SsoLoginEventSerializer(serializers.ModelSerializer):
    organization_slug = serializers.CharField(source="organization.slug", read_only=True)
    identity_provider_name = serializers.CharField(source="identity_provider.name", read_only=True)
    user_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = SsoLoginEvent
        fields = [
            "id",
            "organization",
            "organization_slug",
            "identity_provider",
            "identity_provider_name",
            "user",
            "user_email",
            "email",
            "subject",
            "result",
            "reason",
            "ip_address",
            "user_agent",
            "attributes",
            "created_at",
        ]
        read_only_fields = fields


class SsoTestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False, allow_blank=True)
    subject = serializers.CharField(required=False, allow_blank=True, max_length=255)
    attributes = serializers.JSONField(required=False)

    def create(self, validated_data):
        provider = self.context["provider"]
        request = self.context["request"]
        provider.mark_tested()
        return SsoLoginEvent.objects.create(
            organization=provider.organization,
            identity_provider=provider,
            user=request.user,
            email=validated_data.get("email", request.user.email),
            subject=validated_data.get("subject", "test-subject"),
            result=SsoLoginEvent.Result.TEST,
            reason="manual_connection_test",
            ip_address=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            attributes=validated_data.get("attributes", {}),
        )


class SsoRoutingSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        return value.lower()


class SsoRoutingResultSerializer(serializers.Serializer):
    email = serializers.EmailField()
    domain = serializers.CharField()
    organization = serializers.CharField(allow_null=True)
    sso_required = serializers.BooleanField()
    identity_provider = serializers.DictField(allow_null=True)
    reason = serializers.CharField()
