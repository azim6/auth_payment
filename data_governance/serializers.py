from rest_framework import serializers

from .models import (
    AnonymizationRecord,
    DataAsset,
    DataCategory,
    DataInventorySnapshot,
    DataSubjectRequest,
    LegalHold,
    RetentionJob,
    RetentionPolicy,
)
from .services import create_inventory_snapshot, plan_retention_job, release_legal_hold, run_retention_job


class DataCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = DataCategory
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class DataAssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataAsset
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class RetentionPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = RetentionPolicy
        fields = "__all__"
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)


class LegalHoldSerializer(serializers.ModelSerializer):
    class Meta:
        model = LegalHold
        fields = "__all__"
        read_only_fields = ["id", "released_at", "released_by", "created_by", "created_at"]

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)


class LegalHoldReleaseSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True)

    def save(self, **kwargs):
        return release_legal_hold(self.context["legal_hold"], self.context["request"].user)


class DataSubjectRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataSubjectRequest
        fields = "__all__"
        read_only_fields = ["id", "requested_by", "completed_at", "created_at", "updated_at"]

    def create(self, validated_data):
        validated_data["requested_by"] = self.context["request"].user
        return super().create(validated_data)


class DataSubjectRequestActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["approve", "start", "complete", "reject", "block_by_hold"])
    reason = serializers.CharField(required=False, allow_blank=True)
    evidence_checksum = serializers.CharField(required=False, allow_blank=True, max_length=128)

    def save(self, **kwargs):
        dsr = self.context["request_record"]
        action = self.validated_data["action"]
        if action == "approve":
            dsr.status = DataSubjectRequest.Status.APPROVED
        elif action == "start":
            dsr.status = DataSubjectRequest.Status.IN_PROGRESS
        elif action == "complete":
            dsr.status = DataSubjectRequest.Status.COMPLETED
            from django.utils import timezone
            dsr.completed_at = timezone.now()
            dsr.evidence_checksum = self.validated_data.get("evidence_checksum", dsr.evidence_checksum)
        elif action == "reject":
            dsr.status = DataSubjectRequest.Status.REJECTED
            dsr.rejection_reason = self.validated_data.get("reason", "")
        elif action == "block_by_hold":
            dsr.status = DataSubjectRequest.Status.BLOCKED_BY_HOLD
            dsr.rejection_reason = self.validated_data.get("reason", "Blocked by active legal hold.")
        dsr.save(update_fields=["status", "completed_at", "rejection_reason", "evidence_checksum", "updated_at"])
        return dsr


class RetentionJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = RetentionJob
        fields = "__all__"
        read_only_fields = ["id", "candidate_count", "processed_count", "blocked_count", "result_summary", "error_message", "started_at", "completed_at", "created_by", "created_at"]

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)


class RetentionJobPlanSerializer(serializers.Serializer):
    policy_id = serializers.UUIDField()
    dry_run = serializers.BooleanField(default=True)

    def save(self, **kwargs):
        from .models import RetentionPolicy
        policy = RetentionPolicy.objects.get(id=self.validated_data["policy_id"])
        return plan_retention_job(policy, self.context["request"].user, dry_run=self.validated_data["dry_run"])


class RetentionJobRunSerializer(serializers.Serializer):
    force = serializers.BooleanField(default=False)

    def save(self, **kwargs):
        return run_retention_job(self.context["job"], force=self.validated_data.get("force", False))


class AnonymizationRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnonymizationRecord
        fields = "__all__"
        read_only_fields = ["id", "performed_at"]


class DataInventorySnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataInventorySnapshot
        fields = "__all__"
        read_only_fields = ["id", "generated_at"]


class DataInventorySnapshotCreateSerializer(serializers.Serializer):
    include_assets = serializers.BooleanField(default=True)

    def save(self, **kwargs):
        return create_inventory_snapshot(self.context["request"].user, include_assets=self.validated_data.get("include_assets", True))
