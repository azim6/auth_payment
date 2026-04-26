from rest_framework import serializers

from .models import AccountRecoveryPolicy, IdentityAssuranceEvent, PasskeyChallenge, PasskeyCredential, StepUpPolicy, StepUpSession, TrustedDevice
from .services import issue_passkey_challenge, register_passkey_metadata, remember_trusted_device, satisfy_step_up


class PasskeyCredentialSerializer(serializers.ModelSerializer):
    organization_slug = serializers.CharField(source="organization.slug", read_only=True)

    class Meta:
        model = PasskeyCredential
        fields = [
            "id", "organization", "organization_slug", "label", "credential_id_prefix", "sign_count", "transports", "platform",
            "attestation_type", "aaguid", "backup_eligible", "backup_state", "status", "last_used_at", "revoked_at", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "credential_id_prefix", "sign_count", "last_used_at", "revoked_at", "created_at", "updated_at"]


class PasskeyChallengeCreateSerializer(serializers.Serializer):
    purpose = serializers.ChoiceField(choices=PasskeyChallenge.Purpose.choices)
    rp_id = serializers.CharField(max_length=255)
    origin = serializers.CharField(max_length=255, required=False, allow_blank=True)
    organization = serializers.UUIDField(required=False, allow_null=True)
    lifetime_minutes = serializers.IntegerField(required=False, min_value=1, max_value=30, default=5)
    metadata = serializers.JSONField(required=False)

    def create(self, validated_data):
        organization = None
        org_id = validated_data.get("organization")
        if org_id:
            from accounts.models import Organization
            organization = Organization.objects.get(id=org_id)
        challenge, raw_challenge = issue_passkey_challenge(
            user=self.context["request"].user if self.context["request"].user.is_authenticated else None,
            organization=organization,
            purpose=validated_data["purpose"],
            rp_id=validated_data["rp_id"],
            origin=validated_data.get("origin", ""),
            lifetime_minutes=validated_data.get("lifetime_minutes", 5),
            metadata=validated_data.get("metadata", {}),
        )
        challenge.raw_challenge = raw_challenge
        return challenge

    def to_representation(self, instance):
        return {
            "id": str(instance.id),
            "purpose": instance.purpose,
            "challenge": getattr(instance, "raw_challenge", None),
            "challenge_prefix": instance.challenge_prefix,
            "rp_id": instance.rp_id,
            "origin": instance.origin,
            "expires_at": instance.expires_at,
        }


class PasskeyRegisterCompleteSerializer(serializers.Serializer):
    organization = serializers.UUIDField(required=False, allow_null=True)
    label = serializers.CharField(max_length=160, required=False, allow_blank=True)
    raw_credential_id = serializers.CharField(max_length=512)
    public_key_jwk = serializers.JSONField()
    platform = serializers.ChoiceField(choices=PasskeyCredential.Platform.choices, required=False, default=PasskeyCredential.Platform.UNKNOWN)
    transports = serializers.ListField(child=serializers.CharField(), required=False)
    attestation_type = serializers.CharField(required=False, allow_blank=True)
    aaguid = serializers.CharField(required=False, allow_blank=True)

    def create(self, validated_data):
        organization = None
        org_id = validated_data.get("organization")
        if org_id:
            from accounts.models import Organization
            organization = Organization.objects.get(id=org_id)
        return register_passkey_metadata(
            user=self.context["request"].user,
            organization=organization,
            raw_credential_id=validated_data["raw_credential_id"],
            public_key_jwk=validated_data["public_key_jwk"],
            label=validated_data.get("label", ""),
            platform=validated_data.get("platform", PasskeyCredential.Platform.UNKNOWN),
            transports=validated_data.get("transports", []),
            attestation_type=validated_data.get("attestation_type", ""),
            aaguid=validated_data.get("aaguid", ""),
        )

    def to_representation(self, instance):
        return PasskeyCredentialSerializer(instance).data


class TrustedDeviceSerializer(serializers.ModelSerializer):
    organization_slug = serializers.CharField(source="organization.slug", read_only=True)

    class Meta:
        model = TrustedDevice
        fields = [
            "id", "organization", "organization_slug", "name", "device_prefix", "platform", "trust_level", "status",
            "last_seen_ip", "last_seen_user_agent", "expires_at", "last_seen_at", "revoked_at", "metadata", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "device_prefix", "status", "last_seen_ip", "last_seen_user_agent", "last_seen_at", "revoked_at", "created_at", "updated_at"]


class TrustedDeviceCreateSerializer(serializers.Serializer):
    organization = serializers.UUIDField(required=False, allow_null=True)
    raw_device_id = serializers.CharField(max_length=512)
    name = serializers.CharField(max_length=160)
    platform = serializers.ChoiceField(choices=TrustedDevice.Platform.choices, required=False, default=TrustedDevice.Platform.UNKNOWN)
    trust_level = serializers.ChoiceField(choices=TrustedDevice.TrustLevel.choices, required=False, default=TrustedDevice.TrustLevel.STANDARD)
    expires_at = serializers.DateTimeField(required=False, allow_null=True)
    metadata = serializers.JSONField(required=False)

    def create(self, validated_data):
        organization = None
        org_id = validated_data.get("organization")
        if org_id:
            from accounts.models import Organization
            organization = Organization.objects.get(id=org_id)
        return remember_trusted_device(
            user=self.context["request"].user,
            organization=organization,
            raw_device_id=validated_data["raw_device_id"],
            name=validated_data["name"],
            platform=validated_data.get("platform", TrustedDevice.Platform.UNKNOWN),
            trust_level=validated_data.get("trust_level", TrustedDevice.TrustLevel.STANDARD),
            expires_at=validated_data.get("expires_at"),
            request=self.context.get("request"),
            metadata=validated_data.get("metadata", {}),
        )

    def to_representation(self, instance):
        return TrustedDeviceSerializer(instance).data


class StepUpPolicySerializer(serializers.ModelSerializer):
    organization_slug = serializers.CharField(source="organization.slug", read_only=True)

    class Meta:
        model = StepUpPolicy
        fields = ["id", "organization", "organization_slug", "name", "trigger", "required_method", "max_age_seconds", "min_risk_score", "is_enforced", "metadata", "created_at", "updated_at"]
        read_only_fields = ["id", "organization_slug", "created_at", "updated_at"]


class StepUpSessionSerializer(serializers.ModelSerializer):
    organization_slug = serializers.CharField(source="organization.slug", read_only=True)
    is_valid = serializers.BooleanField(read_only=True)

    class Meta:
        model = StepUpSession
        fields = ["id", "organization", "organization_slug", "method", "trigger", "risk_score", "satisfied_at", "expires_at", "revoked_at", "is_valid", "metadata", "created_at"]
        read_only_fields = fields


class StepUpSatisfySerializer(serializers.Serializer):
    organization = serializers.UUIDField(required=False, allow_null=True)
    trigger = serializers.CharField(max_length=64)
    method = serializers.ChoiceField(choices=StepUpPolicy.RequiredMethod.choices)
    max_age_seconds = serializers.IntegerField(required=False, min_value=60, max_value=86400, default=900)
    risk_score = serializers.IntegerField(required=False, min_value=0, max_value=100, default=0)
    metadata = serializers.JSONField(required=False)

    def create(self, validated_data):
        organization = None
        org_id = validated_data.get("organization")
        if org_id:
            from accounts.models import Organization
            organization = Organization.objects.get(id=org_id)
        return satisfy_step_up(
            user=self.context["request"].user,
            organization=organization,
            trigger=validated_data["trigger"],
            method=validated_data["method"],
            max_age_seconds=validated_data.get("max_age_seconds", 900),
            risk_score=validated_data.get("risk_score", 0),
            request=self.context.get("request"),
            metadata=validated_data.get("metadata", {}),
        )

    def to_representation(self, instance):
        return StepUpSessionSerializer(instance).data


class AccountRecoveryPolicySerializer(serializers.ModelSerializer):
    organization_slug = serializers.CharField(source="organization.slug", read_only=True)

    class Meta:
        model = AccountRecoveryPolicy
        fields = [
            "id", "user", "organization", "organization_slug", "status", "allowed_methods", "require_operator_review",
            "require_mfa_reset_delay", "cooldown_hours", "recovery_contact_email", "metadata", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "organization_slug", "created_at", "updated_at"]


class IdentityAssuranceEventSerializer(serializers.ModelSerializer):
    organization_slug = serializers.CharField(source="organization.slug", read_only=True)

    class Meta:
        model = IdentityAssuranceEvent
        fields = ["id", "user", "organization", "organization_slug", "event_type", "result", "method", "risk_score", "ip_address", "user_agent", "metadata", "created_at"]
        read_only_fields = fields
