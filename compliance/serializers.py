from django.utils import timezone
from rest_framework import serializers

from .models import AdminApprovalRequest, AuditExport, EvidencePack, PolicyDocument, UserPolicyAcceptance
from .services import log_compliance_event


class PolicyDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PolicyDocument
        fields = [
            "id", "policy_type", "version", "title", "body", "document_url", "checksum_sha256",
            "requires_user_acceptance", "requires_admin_acceptance", "is_active", "published_at",
            "retired_at", "created_by", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]

    def create(self, validated_data):
        request = self.context.get("request")
        policy = PolicyDocument.objects.create(created_by=getattr(request, "user", None), **validated_data)
        log_compliance_event(request, "policy_document.created", {"policy_id": str(policy.id), "version": policy.version})
        return policy


class PolicyPublishSerializer(serializers.Serializer):
    def save(self, **kwargs):
        request = self.context["request"]
        policy = self.context["policy"]
        policy.publish(actor=request.user)
        log_compliance_event(request, "policy_document.published", {"policy_id": str(policy.id), "policy_type": policy.policy_type, "version": policy.version})
        return policy


class UserPolicyAcceptanceSerializer(serializers.ModelSerializer):
    policy_version = serializers.CharField(source="policy.version", read_only=True)
    policy_type = serializers.CharField(source="policy.policy_type", read_only=True)

    class Meta:
        model = UserPolicyAcceptance
        fields = [
            "id", "user", "organization", "policy", "policy_type", "policy_version",
            "accepted_at", "ip_address", "user_agent", "metadata",
        ]
        read_only_fields = ["id", "user", "accepted_at", "ip_address", "user_agent"]

    def create(self, validated_data):
        request = self.context["request"]
        acceptance, _ = UserPolicyAcceptance.objects.get_or_create(
            user=request.user,
            organization=validated_data.get("organization"),
            policy=validated_data["policy"],
            defaults={
                "ip_address": request.META.get("REMOTE_ADDR"),
                "user_agent": request.META.get("HTTP_USER_AGENT", ""),
                "metadata": validated_data.get("metadata", {}),
            },
        )
        log_compliance_event(request, "policy_document.accepted", {"policy_id": str(acceptance.policy_id), "organization_id": str(acceptance.organization_id) if acceptance.organization_id else None})
        return acceptance


class AdminApprovalRequestSerializer(serializers.ModelSerializer):
    requested_by_email = serializers.EmailField(source="requested_by.email", read_only=True)
    reviewed_by_email = serializers.EmailField(source="reviewed_by.email", read_only=True)

    class Meta:
        model = AdminApprovalRequest
        fields = [
            "id", "action_type", "status", "requested_by", "requested_by_email", "reviewed_by",
            "reviewed_by_email", "organization", "subject_user", "summary", "reason", "payload",
            "review_notes", "expires_at", "reviewed_at", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "status", "requested_by", "requested_by_email", "reviewed_by", "reviewed_by_email", "reviewed_at", "created_at", "updated_at"]

    def validate(self, attrs):
        expires_at = attrs.get("expires_at")
        if expires_at and expires_at <= timezone.now():
            raise serializers.ValidationError("expires_at must be in the future.")
        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        approval = AdminApprovalRequest.objects.create(requested_by=request.user, **validated_data)
        log_compliance_event(request, "admin_approval.requested", {"approval_id": str(approval.id), "action_type": approval.action_type})
        return approval


class AdminApprovalReviewSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["approve", "reject"])
    notes = serializers.CharField(required=False, allow_blank=True)

    def save(self, **kwargs):
        request = self.context["request"]
        approval = self.context["approval"]
        action = self.validated_data["action"]
        notes = self.validated_data.get("notes", "")
        if action == "approve":
            approval.approve(request.user, notes=notes)
        else:
            approval.reject(request.user, notes=notes)
        log_compliance_event(request, f"admin_approval.{action}", {"approval_id": str(approval.id), "action_type": approval.action_type})
        return approval


class AuditExportSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditExport
        fields = [
            "id", "export_type", "status", "requested_by", "organization", "date_from", "date_to",
            "storage_uri", "checksum_sha256", "record_count", "error_message", "expires_at",
            "completed_at", "created_at",
        ]
        read_only_fields = ["id", "status", "requested_by", "storage_uri", "checksum_sha256", "record_count", "error_message", "completed_at", "created_at"]

    def create(self, validated_data):
        request = self.context["request"]
        export = AuditExport.objects.create(requested_by=request.user, **validated_data)
        log_compliance_event(request, "audit_export.requested", {"export_id": str(export.id), "export_type": export.export_type})
        return export


class AuditExportMarkReadySerializer(serializers.Serializer):
    storage_uri = serializers.CharField(max_length=500)
    checksum_sha256 = serializers.RegexField(regex=r"^[a-fA-F0-9]{64}$")
    record_count = serializers.IntegerField(min_value=0)

    def save(self, **kwargs):
        request = self.context["request"]
        export = self.context["export"]
        export.mark_ready(
            storage_uri=self.validated_data["storage_uri"],
            checksum_sha256=self.validated_data["checksum_sha256"].lower(),
            record_count=self.validated_data["record_count"],
        )
        log_compliance_event(request, "audit_export.ready", {"export_id": str(export.id), "record_count": export.record_count})
        return export


class EvidencePackSerializer(serializers.ModelSerializer):
    class Meta:
        model = EvidencePack
        fields = [
            "id", "pack_type", "status", "title", "organization", "subject_user", "security_incident",
            "audit_exports", "summary", "evidence_index", "locked_by", "locked_at", "created_by",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "status", "locked_by", "locked_at", "created_by", "created_at", "updated_at"]

    def create(self, validated_data):
        request = self.context["request"]
        exports = validated_data.pop("audit_exports", [])
        pack = EvidencePack.objects.create(created_by=request.user, **validated_data)
        if exports:
            pack.audit_exports.set(exports)
        log_compliance_event(request, "evidence_pack.created", {"pack_id": str(pack.id), "pack_type": pack.pack_type})
        return pack


class EvidencePackLockSerializer(serializers.Serializer):
    def save(self, **kwargs):
        request = self.context["request"]
        pack = self.context["pack"]
        pack.lock(request.user)
        log_compliance_event(request, "evidence_pack.locked", {"pack_id": str(pack.id), "pack_type": pack.pack_type})
        return pack
