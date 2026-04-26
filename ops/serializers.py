from rest_framework import serializers

from .models import (
    BackupSnapshot,
    EnvironmentCheck,
    MaintenanceWindow,
    ReleaseRecord,
    RestoreRun,
    ServiceHealthCheck,
    StatusIncident,
)
from .services import mark_release_deployed


class EnvironmentCheckSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnvironmentCheck
        fields = ["id", "key", "status", "message", "details", "checked_at"]
        read_only_fields = fields


class ServiceHealthCheckSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceHealthCheck
        fields = ["id", "name", "status", "latency_ms", "message", "metadata", "checked_at"]
        read_only_fields = fields


class MaintenanceWindowSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaintenanceWindow
        fields = ["id", "title", "status", "starts_at", "ends_at", "affected_services", "customer_message", "internal_notes", "created_by", "created_at", "updated_at", "is_current"]
        read_only_fields = ["id", "created_by", "created_at", "updated_at", "is_current"]

    def create(self, validated_data):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["created_by"] = request.user
        return super().create(validated_data)


class BackupSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = BackupSnapshot
        fields = ["id", "label", "status", "database_name", "storage_uri", "checksum_sha256", "size_bytes", "started_at", "completed_at", "requested_by", "metadata", "error_message", "created_at"]
        read_only_fields = ["id", "requested_by", "created_at"]

    def create(self, validated_data):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["requested_by"] = request.user
        return super().create(validated_data)


class RestoreRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = RestoreRun
        fields = ["id", "backup", "status", "target_environment", "reason", "requested_by", "approved_by", "started_at", "completed_at", "result_notes", "created_at"]
        read_only_fields = ["id", "requested_by", "approved_by", "started_at", "completed_at", "created_at"]

    def create(self, validated_data):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["requested_by"] = request.user
        return super().create(validated_data)


class RestoreApprovalSerializer(serializers.Serializer):
    approve = serializers.BooleanField()
    notes = serializers.CharField(required=False, allow_blank=True)

    def save(self, **kwargs):
        restore = self.context["restore"]
        request = self.context["request"]
        restore.status = RestoreRun.Status.APPROVED if self.validated_data["approve"] else RestoreRun.Status.CANCELLED
        restore.approved_by = request.user
        if self.validated_data.get("notes"):
            restore.result_notes = self.validated_data["notes"]
        restore.save(update_fields=["status", "approved_by", "result_notes"])
        return restore


class StatusIncidentSerializer(serializers.ModelSerializer):
    class Meta:
        model = StatusIncident
        fields = ["id", "title", "state", "impact", "affected_services", "public_message", "internal_notes", "started_at", "resolved_at", "created_by", "created_at", "updated_at"]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]

    def create(self, validated_data):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["created_by"] = request.user
        return super().create(validated_data)


class ReleaseRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReleaseRecord
        fields = ["id", "version", "status", "git_sha", "image_tag", "changelog", "deployed_by", "deployed_at", "rollback_notes", "created_at"]
        read_only_fields = ["id", "deployed_by", "deployed_at", "created_at"]


class ReleaseDeploySerializer(serializers.Serializer):
    mark_deployed = serializers.BooleanField(default=True)

    def save(self, **kwargs):
        release = self.context["release"]
        request = self.context["request"]
        return mark_release_deployed(release, request.user)
