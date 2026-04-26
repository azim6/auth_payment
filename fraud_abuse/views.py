from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AbuseCase, AbuseSignal, DeviceFingerprint, IPReputation, PaymentRiskReview, VelocityEvent, VelocityRule
from .serializers import (
    AbuseCaseActionSerializer,
    AbuseCaseSerializer,
    AbuseSignalSerializer,
    DeviceFingerprintSerializer,
    EnforcementSerializer,
    IPReputationSerializer,
    PaymentRiskReviewActionSerializer,
    PaymentRiskReviewSerializer,
    PromoteSignalSerializer,
    SubjectRiskSummarySerializer,
    VelocityEventRecordSerializer,
    VelocityEventSerializer,
    VelocityRuleSerializer,
)


class StaffOnlyMixin:
    permission_classes = [permissions.IsAdminUser]


class DeviceFingerprintListCreateView(StaffOnlyMixin, generics.ListCreateAPIView):
    serializer_class = DeviceFingerprintSerializer

    def get_queryset(self):
        queryset = DeviceFingerprint.objects.select_related("last_user", "last_organization", "reviewed_by")
        trust_level = self.request.query_params.get("trust_level")
        user_id = self.request.query_params.get("user_id")
        if trust_level:
            queryset = queryset.filter(trust_level=trust_level)
        if user_id:
            queryset = queryset.filter(last_user_id=user_id)
        return queryset


class DeviceFingerprintDetailView(StaffOnlyMixin, generics.RetrieveUpdateAPIView):
    serializer_class = DeviceFingerprintSerializer
    lookup_url_kwarg = "device_id"
    queryset = DeviceFingerprint.objects.select_related("last_user", "last_organization", "reviewed_by")


class IPReputationListCreateView(StaffOnlyMixin, generics.ListCreateAPIView):
    serializer_class = IPReputationSerializer

    def get_queryset(self):
        queryset = IPReputation.objects.all()
        reputation = self.request.query_params.get("reputation")
        min_score = self.request.query_params.get("min_score")
        if reputation:
            queryset = queryset.filter(reputation=reputation)
        if min_score:
            queryset = queryset.filter(risk_score__gte=min_score)
        return queryset


class IPReputationDetailView(StaffOnlyMixin, generics.RetrieveUpdateAPIView):
    serializer_class = IPReputationSerializer
    lookup_url_kwarg = "ip_id"
    queryset = IPReputation.objects.all()


class AbuseSignalListCreateView(StaffOnlyMixin, generics.ListCreateAPIView):
    serializer_class = AbuseSignalSerializer

    def get_queryset(self):
        queryset = AbuseSignal.objects.select_related("user", "organization", "subscription", "device", "ip_reputation")
        category = self.request.query_params.get("category")
        severity = self.request.query_params.get("severity")
        user_id = self.request.query_params.get("user_id")
        organization_id = self.request.query_params.get("organization_id")
        signal = self.request.query_params.get("signal")
        if category:
            queryset = queryset.filter(category=category)
        if severity:
            queryset = queryset.filter(severity=severity)
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        if organization_id:
            queryset = queryset.filter(organization_id=organization_id)
        if signal:
            queryset = queryset.filter(signal=signal)
        return queryset


class AbuseSignalPromoteView(StaffOnlyMixin, APIView):
    def post(self, request, signal_id):
        signal = get_object_or_404(AbuseSignal, id=signal_id)
        serializer = PromoteSignalSerializer(data=request.data, context={"request": request, "signal": signal})
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return Response({
            "security_risk_id": str(result["security_risk"].id) if result.get("security_risk") else None,
            "case_id": str(result["case"].id) if result.get("case") else None,
        }, status=status.HTTP_201_CREATED)


class VelocityRuleListCreateView(StaffOnlyMixin, generics.ListCreateAPIView):
    serializer_class = VelocityRuleSerializer

    def get_queryset(self):
        queryset = VelocityRule.objects.all()
        event_name = self.request.query_params.get("event_name")
        scope = self.request.query_params.get("scope")
        enabled = self.request.query_params.get("enabled")
        if event_name:
            queryset = queryset.filter(event_name=event_name)
        if scope:
            queryset = queryset.filter(scope=scope)
        if enabled in {"1", "true", "yes"}:
            queryset = queryset.filter(enabled=True)
        elif enabled in {"0", "false", "no"}:
            queryset = queryset.filter(enabled=False)
        return queryset


class VelocityRuleDetailView(StaffOnlyMixin, generics.RetrieveUpdateAPIView):
    serializer_class = VelocityRuleSerializer
    lookup_url_kwarg = "rule_id"
    queryset = VelocityRule.objects.all()


class VelocityEventListView(StaffOnlyMixin, generics.ListAPIView):
    serializer_class = VelocityEventSerializer

    def get_queryset(self):
        queryset = VelocityEvent.objects.select_related("user", "organization", "device")
        event_name = self.request.query_params.get("event_name")
        user_id = self.request.query_params.get("user_id")
        organization_id = self.request.query_params.get("organization_id")
        if event_name:
            queryset = queryset.filter(event_name=event_name)
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        if organization_id:
            queryset = queryset.filter(organization_id=organization_id)
        return queryset


class VelocityEventRecordView(StaffOnlyMixin, APIView):
    def post(self, request):
        serializer = VelocityEventRecordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return Response({
            "event": VelocityEventSerializer(result["event"]).data,
            "matches": [
                {
                    "rule_id": str(match["rule"].id),
                    "count": match["count"],
                    "signal_id": str(match["signal"].id),
                    "action": match["rule"].action,
                }
                for match in result["matches"]
            ],
        }, status=status.HTTP_201_CREATED)


class AbuseCaseListCreateView(StaffOnlyMixin, generics.ListCreateAPIView):
    serializer_class = AbuseCaseSerializer

    def get_queryset(self):
        queryset = AbuseCase.objects.select_related("user", "organization", "owner").prefetch_related("signals")
        status_value = self.request.query_params.get("status")
        case_type = self.request.query_params.get("case_type")
        severity = self.request.query_params.get("severity")
        if status_value:
            queryset = queryset.filter(status=status_value)
        if case_type:
            queryset = queryset.filter(case_type=case_type)
        if severity:
            queryset = queryset.filter(severity=severity)
        return queryset


class AbuseCaseDetailView(StaffOnlyMixin, generics.RetrieveUpdateAPIView):
    serializer_class = AbuseCaseSerializer
    lookup_url_kwarg = "case_id"
    queryset = AbuseCase.objects.select_related("user", "organization", "owner").prefetch_related("signals")


class AbuseCaseActionView(StaffOnlyMixin, APIView):
    def post(self, request, case_id):
        case = get_object_or_404(AbuseCase, id=case_id)
        serializer = AbuseCaseActionSerializer(data=request.data, context={"request": request, "case": case})
        serializer.is_valid(raise_exception=True)
        case = serializer.save()
        return Response(AbuseCaseSerializer(case).data)


class PaymentRiskReviewListCreateView(StaffOnlyMixin, generics.ListCreateAPIView):
    serializer_class = PaymentRiskReviewSerializer

    def get_queryset(self):
        queryset = PaymentRiskReview.objects.select_related("organization", "customer", "subscription", "invoice", "transaction", "reviewed_by").prefetch_related("signals")
        status_value = self.request.query_params.get("status")
        organization_id = self.request.query_params.get("organization_id")
        if status_value:
            queryset = queryset.filter(status=status_value)
        if organization_id:
            queryset = queryset.filter(organization_id=organization_id)
        return queryset


class PaymentRiskReviewActionView(StaffOnlyMixin, APIView):
    def post(self, request, review_id):
        review = get_object_or_404(PaymentRiskReview, id=review_id)
        serializer = PaymentRiskReviewActionSerializer(data=request.data, context={"request": request, "review": review})
        serializer.is_valid(raise_exception=True)
        review = serializer.save()
        return Response(PaymentRiskReviewSerializer(review).data)


class EnforcementView(StaffOnlyMixin, APIView):
    def post(self, request):
        serializer = EnforcementSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        restriction = serializer.save()
        return Response({"restriction_id": str(restriction.id), "restriction_type": restriction.restriction_type}, status=status.HTTP_201_CREATED)


class SubjectRiskSummaryView(StaffOnlyMixin, APIView):
    def post(self, request):
        serializer = SubjectRiskSummarySerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return Response({
            "max_recent_score": result["max_recent_score"],
            "recent_signal_count": result["recent_signal_count"],
            "open_case_count": result["open_case_count"],
            "pending_payment_review_count": result["pending_payment_review_count"],
            "active_restriction_count": result["active_restriction_count"],
            "recent_signals": AbuseSignalSerializer(result["recent_signals"], many=True).data,
        })
