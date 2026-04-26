from rest_framework import serializers

from .models import (
    DevicePushToken,
    NotificationDelivery,
    NotificationEvent,
    NotificationPreference,
    NotificationProvider,
    NotificationSuppression,
    NotificationTemplate,
)
from .services import create_notification_event, enqueue_deliveries


class NotificationProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationProvider
        fields = ["id", "name", "channel", "provider_code", "status", "priority", "config", "last_success_at", "last_failure_at", "created_at", "updated_at"]
        read_only_fields = ["id", "last_success_at", "last_failure_at", "created_at", "updated_at"]


class NotificationTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationTemplate
        fields = ["id", "key", "channel", "locale", "project", "organization", "version", "is_active", "subject_template", "body_template", "html_template", "variables_schema", "created_by", "created_at", "updated_at"]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = ["id", "user", "organization", "topic", "channel", "enabled", "locale", "timezone", "quiet_hours_start", "quiet_hours_end", "metadata", "created_at", "updated_at"]
        read_only_fields = ["id", "user", "created_at", "updated_at"]


class DevicePushTokenSerializer(serializers.ModelSerializer):
    raw_token = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = DevicePushToken
        fields = ["id", "user", "organization", "platform", "device_id", "raw_token", "token_prefix", "is_active", "last_used_at", "revoked_at", "created_at", "updated_at"]
        read_only_fields = ["id", "user", "token_prefix", "is_active", "last_used_at", "revoked_at", "created_at", "updated_at"]

    def create(self, validated_data):
        raw_token = validated_data.pop("raw_token")
        request = self.context["request"]
        token_hash = DevicePushToken.hash_token(raw_token)
        token, _ = DevicePushToken.objects.update_or_create(
            token_hash=token_hash,
            defaults={
                "user": request.user,
                "organization": validated_data.get("organization"),
                "platform": validated_data["platform"],
                "device_id": validated_data.get("device_id", ""),
                "token_prefix": DevicePushToken.prefix_token(raw_token),
                "is_active": True,
                "revoked_at": None,
            },
        )
        return token


class NotificationEventSerializer(serializers.ModelSerializer):
    channels = serializers.ListField(child=serializers.CharField(), write_only=True, required=False)

    class Meta:
        model = NotificationEvent
        fields = ["id", "organization", "user", "project", "event_type", "topic", "priority", "status", "idempotency_key", "payload", "scheduled_for", "created_by", "created_at", "updated_at", "channels"]
        read_only_fields = ["id", "status", "created_by", "created_at", "updated_at"]

    def create(self, validated_data):
        channels = validated_data.pop("channels", None)
        request = self.context["request"]
        event = create_notification_event(created_by=request.user, **validated_data)
        enqueue_deliveries(event, channels=channels)
        return event


class NotificationDeliverySerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationDelivery
        fields = ["id", "event", "template", "provider", "channel", "recipient", "recipient_hash", "subject", "body", "html_body", "status", "attempt_count", "max_attempts", "next_attempt_at", "last_attempt_at", "sent_at", "provider_message_id", "error_message", "metadata", "created_at", "updated_at"]
        read_only_fields = fields


class NotificationSuppressionSerializer(serializers.ModelSerializer):
    recipient = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = NotificationSuppression
        fields = ["id", "channel", "recipient", "recipient_hash", "reason", "note", "expires_at", "created_by", "created_at"]
        read_only_fields = ["id", "recipient_hash", "created_by", "created_at"]

    def create(self, validated_data):
        from .services import hash_recipient

        recipient = validated_data.pop("recipient", "")
        validated_data["recipient_hash"] = validated_data.get("recipient_hash") or hash_recipient(recipient)
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)


class NotificationSummarySerializer(serializers.Serializer):
    organization = serializers.UUIDField(required=False, allow_null=True)
    pending = serializers.IntegerField()
    sent = serializers.IntegerField()
    failed = serializers.IntegerField()
    dead = serializers.IntegerField()
    templates = serializers.IntegerField()
    active_providers = serializers.IntegerField()
