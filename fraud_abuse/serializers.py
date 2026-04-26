from rest_framework import serializers

from .models import AbuseCase, AbuseSignal, DeviceFingerprint, IPReputation, PaymentRiskReview, VelocityEvent, VelocityRule
from .services import apply_safe_enforcement, create_security_risk_from_abuse_signal, evaluate_velocity_rules, record_velocity_event, summarize_subject_risk


class DeviceFingerprintSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceFingerprint
        fields = "__all__"
        read_only_fields = ["id", "first_seen_at", "last_seen_at", "created_at", "updated_at"]


class IPReputationSerializer(serializers.ModelSerializer):
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = IPReputation
        fields = "__all__"
        read_only_fields = ["id", "first_seen_at", "last_seen_at", "created_at", "updated_at", "is_active"]


class AbuseSignalSerializer(serializers.ModelSerializer):
    class Meta:
        model = AbuseSignal
        fields = "__all__"
        read_only_fields = ["id", "created_at"]


class VelocityRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = VelocityRule
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class VelocityEventSerializer(serializers.ModelSerializer):
    matched_rules = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = VelocityEvent
        fields = "__all__"
        read_only_fields = ["id", "created_at", "matched_rules"]

    def get_matched_rules(self, obj):
        return []


class VelocityEventRecordSerializer(serializers.Serializer):
    event_name = serializers.CharField(max_length=120)
    user = serializers.UUIDField(required=False, allow_null=True)
    organization = serializers.UUIDField(required=False, allow_null=True)
    device = serializers.UUIDField(required=False, allow_null=True)
    ip_address = serializers.IPAddressField(required=False, allow_null=True)
    metadata = serializers.JSONField(required=False)

    def save(self, **kwargs):
        from django.contrib.auth import get_user_model
        from accounts.models import Organization

        User = get_user_model()
        data = self.validated_data
        user = User.objects.filter(id=data.get("user")).first() if data.get("user") else None
        organization = Organization.objects.filter(id=data.get("organization")).first() if data.get("organization") else None
        device = DeviceFingerprint.objects.filter(id=data.get("device")).first() if data.get("device") else None
        event = record_velocity_event(
            event_name=data["event_name"],
            user=user,
            organization=organization,
            device=device,
            ip_address=data.get("ip_address"),
            metadata=data.get("metadata") or {},
        )
        matches = evaluate_velocity_rules(event)
        return {"event": event, "matches": matches}


class AbuseCaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = AbuseCase
        fields = "__all__"
        read_only_fields = ["id", "opened_at", "resolved_at", "created_at", "updated_at"]


class AbuseCaseActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["review", "mitigate", "resolve", "false_positive"])
    notes = serializers.CharField(required=False, allow_blank=True)

    def save(self, **kwargs):
        from django.utils import timezone

        case = self.context["case"]
        action = self.validated_data["action"]
        notes = self.validated_data.get("notes", "")
        if action == "review":
            case.status = AbuseCase.Status.REVIEWING
        elif action == "mitigate":
            case.status = AbuseCase.Status.MITIGATED
        elif action == "resolve":
            case.status = AbuseCase.Status.RESOLVED
            case.resolved_at = timezone.now()
        elif action == "false_positive":
            case.status = AbuseCase.Status.FALSE_POSITIVE
            case.resolved_at = timezone.now()
        if notes:
            case.resolution_notes = notes
        case.save(update_fields=["status", "resolution_notes", "resolved_at", "updated_at"])
        return case


class PaymentRiskReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentRiskReview
        fields = "__all__"
        read_only_fields = ["id", "reviewed_by", "reviewed_at", "created_at", "updated_at"]


class PaymentRiskReviewActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["approve", "reject", "escalate"])
    notes = serializers.CharField(required=False, allow_blank=True)

    def save(self, **kwargs):
        review = self.context["review"]
        actor = self.context["request"].user
        status_map = {
            "approve": PaymentRiskReview.Status.APPROVED,
            "reject": PaymentRiskReview.Status.REJECTED,
            "escalate": PaymentRiskReview.Status.ESCALATED,
        }
        review.apply_decision(actor, status_map[self.validated_data["action"]], self.validated_data.get("notes", ""))
        return review


class EnforcementSerializer(serializers.Serializer):
    user = serializers.UUIDField()
    organization = serializers.UUIDField(required=False, allow_null=True)
    restriction_type = serializers.CharField(default="api_block")
    reason = serializers.CharField()
    expires_at = serializers.DateTimeField(required=False, allow_null=True)
    metadata = serializers.JSONField(required=False)

    def save(self, **kwargs):
        from django.contrib.auth import get_user_model
        from accounts.models import Organization

        User = get_user_model()
        user = User.objects.get(id=self.validated_data["user"])
        org_id = self.validated_data.get("organization")
        organization = Organization.objects.filter(id=org_id).first() if org_id else None
        return apply_safe_enforcement(
            user=user,
            organization=organization,
            restriction_type=self.validated_data.get("restriction_type"),
            reason=self.validated_data["reason"],
            actor=self.context["request"].user,
            expires_at=self.validated_data.get("expires_at"),
            metadata=self.validated_data.get("metadata") or {},
        )


class PromoteSignalSerializer(serializers.Serializer):
    create_security_risk = serializers.BooleanField(default=True)
    create_case = serializers.BooleanField(default=False)
    case_type = serializers.CharField(default="other")
    case_title = serializers.CharField(required=False, allow_blank=True)

    def save(self, **kwargs):
        signal = self.context["signal"]
        result = {"security_risk": None, "case": None}
        if self.validated_data.get("create_security_risk"):
            result["security_risk"] = create_security_risk_from_abuse_signal(signal)
        if self.validated_data.get("create_case"):
            case = AbuseCase.objects.create(
                case_type=self.validated_data.get("case_type") or AbuseCase.CaseType.OTHER,
                severity=signal.severity,
                title=self.validated_data.get("case_title") or signal.summary,
                user=signal.user,
                organization=signal.organization,
                summary=signal.summary,
            )
            case.signals.add(signal)
            result["case"] = case
        return result


class SubjectRiskSummarySerializer(serializers.Serializer):
    user = serializers.UUIDField(required=False, allow_null=True)
    organization = serializers.UUIDField(required=False, allow_null=True)
    ip_address = serializers.IPAddressField(required=False, allow_null=True)

    def save(self, **kwargs):
        from django.contrib.auth import get_user_model
        from accounts.models import Organization

        User = get_user_model()
        data = self.validated_data
        user = User.objects.filter(id=data.get("user")).first() if data.get("user") else None
        organization = Organization.objects.filter(id=data.get("organization")).first() if data.get("organization") else None
        return summarize_subject_risk(user=user, organization=organization, ip_address=data.get("ip_address"))
