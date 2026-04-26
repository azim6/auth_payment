from rest_framework import serializers

from .models import PortalActivityLog, PortalApiKey, PortalOrganizationBookmark, PortalProfileSettings, PortalSupportRequest
from .services import create_portal_api_key, validate_portal_scopes


class PortalProfileSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PortalProfileSettings
        fields = [
            "id", "display_name", "preferred_locale", "timezone", "theme", "marketing_opt_in",
            "security_emails_enabled", "product_emails_enabled", "metadata", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class PortalOrganizationBookmarkSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(source="organization.name", read_only=True)
    organization_slug = serializers.CharField(source="organization.slug", read_only=True)

    class Meta:
        model = PortalOrganizationBookmark
        fields = ["id", "organization", "organization_name", "organization_slug", "label", "sort_order", "created_at"]
        read_only_fields = ["id", "organization_name", "organization_slug", "created_at"]


class PortalApiKeySerializer(serializers.ModelSerializer):
    organization_slug = serializers.CharField(source="organization.slug", read_only=True)

    class Meta:
        model = PortalApiKey
        fields = [
            "id", "organization", "organization_slug", "name", "key_prefix", "scopes", "status",
            "allowed_origins", "allowed_ips", "expires_at", "last_used_at", "revoked_at", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "key_prefix", "status", "last_used_at", "revoked_at", "created_at", "updated_at"]


class PortalApiKeyCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=160)
    organization = serializers.UUIDField(required=False, allow_null=True)
    scopes = serializers.CharField(required=False, allow_blank=True)
    expires_at = serializers.DateTimeField(required=False, allow_null=True)
    allowed_origins = serializers.ListField(child=serializers.CharField(), required=False)
    allowed_ips = serializers.ListField(child=serializers.CharField(), required=False)

    def validate_scopes(self, value):
        try:
            return validate_portal_scopes(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc

    def create(self, validated_data):
        from accounts.models import Organization
        organization = None
        organization_id = validated_data.get("organization")
        if organization_id:
            organization = Organization.objects.get(id=organization_id)
        key, raw_key = create_portal_api_key(
            user=self.context["request"].user,
            organization=organization,
            name=validated_data["name"],
            scopes=validated_data.get("scopes", ""),
            expires_at=validated_data.get("expires_at"),
            allowed_origins=validated_data.get("allowed_origins", []),
            allowed_ips=validated_data.get("allowed_ips", []),
        )
        key.raw_key = raw_key
        return key

    def to_representation(self, instance):
        data = PortalApiKeySerializer(instance).data
        data["raw_key"] = getattr(instance, "raw_key", None)
        return data


class PortalSupportRequestSerializer(serializers.ModelSerializer):
    organization_slug = serializers.CharField(source="organization.slug", read_only=True)

    class Meta:
        model = PortalSupportRequest
        fields = [
            "id", "organization", "organization_slug", "category", "status", "subject", "message", "priority",
            "related_object_type", "related_object_id", "metadata", "created_at", "updated_at", "resolved_at",
        ]
        read_only_fields = ["id", "status", "organization_slug", "created_at", "updated_at", "resolved_at"]


class PortalActivityLogSerializer(serializers.ModelSerializer):
    organization_slug = serializers.CharField(source="organization.slug", read_only=True)

    class Meta:
        model = PortalActivityLog
        fields = ["id", "organization", "organization_slug", "domain", "event_type", "title", "summary", "ip_address", "metadata", "created_at"]
        read_only_fields = fields
