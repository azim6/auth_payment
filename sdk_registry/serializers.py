from rest_framework import serializers

from .models import IntegrationGuide, SdkCompatibilityMatrix, SdkRelease, SdkTelemetryEvent


class SdkReleaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = SdkRelease
        fields = [
            "id",
            "platform",
            "version",
            "status",
            "download_url",
            "checksum_sha256",
            "minimum_api_version",
            "release_notes",
            "breaking_changes",
            "published_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "published_at", "created_at", "updated_at"]


class IntegrationGuideSerializer(serializers.ModelSerializer):
    class Meta:
        model = IntegrationGuide
        fields = ["id", "slug", "title", "audience", "summary", "content_markdown", "is_published", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class SdkCompatibilityMatrixSerializer(serializers.ModelSerializer):
    class Meta:
        model = SdkCompatibilityMatrix
        fields = [
            "id",
            "sdk_platform",
            "sdk_version",
            "api_version",
            "min_server_version",
            "max_server_version",
            "supports_pkce",
            "supports_refresh_rotation",
            "supports_step_up",
            "supports_passkeys",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class SdkTelemetryEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = SdkTelemetryEvent
        fields = [
            "id",
            "organization_id",
            "application_id",
            "platform",
            "sdk_version",
            "event_type",
            "event_name",
            "user_agent",
            "ip_address",
            "metadata",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]
