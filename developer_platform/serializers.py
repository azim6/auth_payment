from rest_framework import serializers

from accounts.models import Organization

from .models import DeveloperApplication, IntegrationAuditEvent, SDKTokenPolicy, WebhookDelivery, WebhookSubscription
from .services import create_application_with_secret, create_webhook_subscription_with_secret


class DeveloperApplicationSerializer(serializers.ModelSerializer):
    raw_client_secret = serializers.CharField(read_only=True)

    class Meta:
        model = DeveloperApplication
        fields = [
            "id", "organization", "project", "name", "slug", "app_type", "environment", "status",
            "client_id", "client_secret_prefix", "raw_client_secret", "redirect_uris", "allowed_origins",
            "allowed_package_names", "allowed_bundle_ids", "allowed_scopes", "token_ttl_seconds",
            "require_pkce", "require_mfa", "created_by", "last_used_at", "metadata", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "client_id", "client_secret_prefix", "raw_client_secret", "created_by", "last_used_at", "created_at", "updated_at"]

    def create(self, validated_data):
        request = self.context["request"]
        app, raw_secret = create_application_with_secret(
            organization=validated_data.pop("organization"),
            created_by=request.user,
            request=request,
            **validated_data,
        )
        app.raw_client_secret = raw_secret or ""
        return app


class DeveloperApplicationRotateSecretSerializer(serializers.Serializer):
    raw_client_secret = serializers.CharField(read_only=True)


class SDKTokenPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = SDKTokenPolicy
        fields = ["id", "application", "platform", "allow_public_client", "require_device_binding", "require_attestation", "max_token_ttl_seconds", "allowed_scopes", "notes", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class WebhookSubscriptionSerializer(serializers.ModelSerializer):
    raw_webhook_secret = serializers.CharField(read_only=True)

    class Meta:
        model = WebhookSubscription
        fields = ["id", "organization", "application", "name", "target_url", "status", "event_types", "secret_prefix", "raw_webhook_secret", "max_attempts", "last_success_at", "last_failure_at", "created_by", "metadata", "created_at", "updated_at"]
        read_only_fields = ["id", "secret_prefix", "raw_webhook_secret", "last_success_at", "last_failure_at", "created_by", "created_at", "updated_at"]

    def validate(self, attrs):
        organization = attrs.get("organization") or getattr(self.instance, "organization", None)
        application = attrs.get("application") or getattr(self.instance, "application", None)
        if organization and application and application.organization_id != organization.id:
            raise serializers.ValidationError("Application must belong to the same organization as the webhook subscription.")
        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        subscription, raw_secret = create_webhook_subscription_with_secret(
            organization=validated_data.pop("organization"),
            application=validated_data.pop("application"),
            created_by=request.user,
            request=request,
            **validated_data,
        )
        subscription.raw_webhook_secret = raw_secret
        return subscription


class WebhookSecretRotateSerializer(serializers.Serializer):
    raw_webhook_secret = serializers.CharField(read_only=True)


class WebhookDeliverySerializer(serializers.ModelSerializer):
    class Meta:
        model = WebhookDelivery
        fields = ["id", "subscription", "event_id", "event_type", "payload", "status", "attempt_count", "next_attempt_at", "response_status_code", "response_body", "error_message", "delivered_at", "created_at", "updated_at"]
        read_only_fields = fields


class IntegrationAuditEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = IntegrationAuditEvent
        fields = ["id", "organization", "actor", "application", "action", "target_type", "target_id", "ip_address", "user_agent", "metadata", "created_at"]
        read_only_fields = fields


class IntegrationSummarySerializer(serializers.Serializer):
    organization = serializers.UUIDField()
    slug = serializers.CharField()
    applications = serializers.IntegerField()
    active_webhooks = serializers.IntegerField()
    pending_deliveries = serializers.IntegerField()
    failed_deliveries = serializers.IntegerField()
