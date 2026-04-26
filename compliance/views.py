from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AdminApprovalRequest, AuditExport, EvidencePack, PolicyDocument, UserPolicyAcceptance
from .serializers import (
    AdminApprovalRequestSerializer,
    AdminApprovalReviewSerializer,
    AuditExportMarkReadySerializer,
    AuditExportSerializer,
    EvidencePackLockSerializer,
    EvidencePackSerializer,
    PolicyDocumentSerializer,
    PolicyPublishSerializer,
    UserPolicyAcceptanceSerializer,
)


class StaffOnlyMixin:
    permission_classes = [permissions.IsAdminUser]


class PolicyDocumentListCreateView(StaffOnlyMixin, generics.ListCreateAPIView):
    serializer_class = PolicyDocumentSerializer

    def get_queryset(self):
        queryset = PolicyDocument.objects.select_related("created_by")
        policy_type = self.request.query_params.get("policy_type")
        active = self.request.query_params.get("active")
        if policy_type:
            queryset = queryset.filter(policy_type=policy_type)
        if active in {"1", "true", "yes"}:
            queryset = queryset.filter(is_active=True)
        return queryset


class PolicyDocumentDetailView(StaffOnlyMixin, generics.RetrieveUpdateAPIView):
    serializer_class = PolicyDocumentSerializer
    queryset = PolicyDocument.objects.select_related("created_by")
    lookup_url_kwarg = "policy_id"


class PolicyPublishView(StaffOnlyMixin, APIView):
    def post(self, request, policy_id):
        policy = get_object_or_404(PolicyDocument, id=policy_id)
        serializer = PolicyPublishSerializer(data=request.data, context={"request": request, "policy": policy})
        serializer.is_valid(raise_exception=True)
        policy = serializer.save()
        return Response(PolicyDocumentSerializer(policy).data)


class ActivePolicyListView(generics.ListAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = PolicyDocumentSerializer

    def get_queryset(self):
        return PolicyDocument.objects.filter(is_active=True, retired_at__isnull=True)


class UserPolicyAcceptanceListCreateView(generics.ListCreateAPIView):
    serializer_class = UserPolicyAcceptanceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return UserPolicyAcceptance.objects.filter(user=self.request.user).select_related("policy", "organization")


class AdminApprovalRequestListCreateView(StaffOnlyMixin, generics.ListCreateAPIView):
    serializer_class = AdminApprovalRequestSerializer

    def get_queryset(self):
        queryset = AdminApprovalRequest.objects.select_related("requested_by", "reviewed_by", "organization", "subject_user")
        status_value = self.request.query_params.get("status")
        action_type = self.request.query_params.get("action_type")
        organization_id = self.request.query_params.get("organization_id")
        if status_value:
            queryset = queryset.filter(status=status_value)
        if action_type:
            queryset = queryset.filter(action_type=action_type)
        if organization_id:
            queryset = queryset.filter(organization_id=organization_id)
        return queryset


class AdminApprovalReviewView(StaffOnlyMixin, APIView):
    def post(self, request, approval_id):
        approval = get_object_or_404(AdminApprovalRequest, id=approval_id)
        serializer = AdminApprovalReviewSerializer(data=request.data, context={"request": request, "approval": approval})
        serializer.is_valid(raise_exception=True)
        approval = serializer.save()
        return Response(AdminApprovalRequestSerializer(approval).data)


class AuditExportListCreateView(StaffOnlyMixin, generics.ListCreateAPIView):
    serializer_class = AuditExportSerializer

    def get_queryset(self):
        queryset = AuditExport.objects.select_related("requested_by", "organization")
        export_type = self.request.query_params.get("export_type")
        status_value = self.request.query_params.get("status")
        organization_id = self.request.query_params.get("organization_id")
        if export_type:
            queryset = queryset.filter(export_type=export_type)
        if status_value:
            queryset = queryset.filter(status=status_value)
        if organization_id:
            queryset = queryset.filter(organization_id=organization_id)
        return queryset


class AuditExportMarkReadyView(StaffOnlyMixin, APIView):
    def post(self, request, export_id):
        export = get_object_or_404(AuditExport, id=export_id)
        serializer = AuditExportMarkReadySerializer(data=request.data, context={"request": request, "export": export})
        serializer.is_valid(raise_exception=True)
        export = serializer.save()
        return Response(AuditExportSerializer(export).data)


class EvidencePackListCreateView(StaffOnlyMixin, generics.ListCreateAPIView):
    serializer_class = EvidencePackSerializer

    def get_queryset(self):
        queryset = EvidencePack.objects.select_related("organization", "subject_user", "security_incident", "locked_by", "created_by").prefetch_related("audit_exports")
        pack_type = self.request.query_params.get("pack_type")
        status_value = self.request.query_params.get("status")
        organization_id = self.request.query_params.get("organization_id")
        if pack_type:
            queryset = queryset.filter(pack_type=pack_type)
        if status_value:
            queryset = queryset.filter(status=status_value)
        if organization_id:
            queryset = queryset.filter(organization_id=organization_id)
        return queryset


class EvidencePackDetailView(StaffOnlyMixin, generics.RetrieveUpdateAPIView):
    serializer_class = EvidencePackSerializer
    lookup_url_kwarg = "pack_id"
    queryset = EvidencePack.objects.select_related("organization", "subject_user", "security_incident", "locked_by", "created_by").prefetch_related("audit_exports")


class EvidencePackLockView(StaffOnlyMixin, APIView):
    def post(self, request, pack_id):
        pack = get_object_or_404(EvidencePack, id=pack_id)
        serializer = EvidencePackLockSerializer(data=request.data, context={"request": request, "pack": pack})
        serializer.is_valid(raise_exception=True)
        pack = serializer.save()
        return Response(EvidencePackSerializer(pack).data)
