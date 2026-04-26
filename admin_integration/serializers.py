from rest_framework import serializers

from .models import AdminApiContractEndpoint, AdminApiScope, AdminRequestAudit, AdminServiceCredential


class AdminApiScopeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdminApiScope
        fields = ["id", "code", "title", "description", "risk", "requires_two_person_approval", "enabled", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class AdminServiceCredentialSerializer(serializers.ModelSerializer):
    scope_list = serializers.SerializerMethodField()

    class Meta:
        model = AdminServiceCredential
        fields = ["id", "name", "key_prefix", "signing_key_id", "scopes", "scope_list", "allowed_ips", "is_active", "expires_at", "last_used_at", "rotated_at", "created_at", "updated_at"]
        read_only_fields = ["id", "key_prefix", "signing_key_id", "last_used_at", "rotated_at", "created_at", "updated_at"]

    def get_scope_list(self, obj):
        return sorted(obj.scope_set)


class AdminServiceCredentialCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=180)
    scopes = serializers.CharField(default="admin:readiness admin:read")
    allowed_ips = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    expires_at = serializers.DateTimeField(required=False, allow_null=True)


class AdminRequestAuditSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdminRequestAudit
        fields = ["id", "credential", "key_prefix", "method", "path", "nonce", "timestamp", "ip_address", "decision", "status_code", "latency_ms", "error", "metadata", "created_at"]
        read_only_fields = fields


class AdminApiContractEndpointSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdminApiContractEndpoint
        fields = ["id", "domain", "method", "path", "required_scope", "description", "stable", "enabled", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]
