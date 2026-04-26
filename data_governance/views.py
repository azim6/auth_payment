from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

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
from .serializers import (
    AnonymizationRecordSerializer,
    DataAssetSerializer,
    DataCategorySerializer,
    DataInventorySnapshotCreateSerializer,
    DataInventorySnapshotSerializer,
    DataSubjectRequestActionSerializer,
    DataSubjectRequestSerializer,
    LegalHoldReleaseSerializer,
    LegalHoldSerializer,
    RetentionJobPlanSerializer,
    RetentionJobRunSerializer,
    RetentionJobSerializer,
    RetentionPolicySerializer,
)
from .services import governance_summary


class StaffOnlyMixin:
    permission_classes = [permissions.IsAdminUser]


class GovernanceSummaryView(StaffOnlyMixin, APIView):
    def get(self, request):
        return Response(governance_summary())


class DataCategoryListCreateView(StaffOnlyMixin, generics.ListCreateAPIView):
    serializer_class = DataCategorySerializer
    queryset = DataCategory.objects.all()


class DataCategoryDetailView(StaffOnlyMixin, generics.RetrieveUpdateAPIView):
    serializer_class = DataCategorySerializer
    queryset = DataCategory.objects.all()
    lookup_url_kwarg = "category_id"


class DataAssetListCreateView(StaffOnlyMixin, generics.ListCreateAPIView):
    serializer_class = DataAssetSerializer

    def get_queryset(self):
        queryset = DataAsset.objects.prefetch_related("categories")
        app_label = self.request.query_params.get("app_label")
        contains_pii = self.request.query_params.get("contains_pii")
        if app_label:
            queryset = queryset.filter(app_label=app_label)
        if contains_pii in {"true", "false"}:
            queryset = queryset.filter(contains_pii=contains_pii == "true")
        return queryset


class DataAssetDetailView(StaffOnlyMixin, generics.RetrieveUpdateAPIView):
    serializer_class = DataAssetSerializer
    queryset = DataAsset.objects.prefetch_related("categories")
    lookup_url_kwarg = "asset_id"


class RetentionPolicyListCreateView(StaffOnlyMixin, generics.ListCreateAPIView):
    serializer_class = RetentionPolicySerializer
    queryset = RetentionPolicy.objects.prefetch_related("assets", "categories").select_related("created_by")


class RetentionPolicyDetailView(StaffOnlyMixin, generics.RetrieveUpdateAPIView):
    serializer_class = RetentionPolicySerializer
    queryset = RetentionPolicy.objects.prefetch_related("assets", "categories").select_related("created_by")
    lookup_url_kwarg = "policy_id"


class LegalHoldListCreateView(StaffOnlyMixin, generics.ListCreateAPIView):
    serializer_class = LegalHoldSerializer

    def get_queryset(self):
        queryset = LegalHold.objects.select_related("user", "organization", "category", "created_by", "released_by")
        status_value = self.request.query_params.get("status")
        scope = self.request.query_params.get("scope")
        if status_value:
            queryset = queryset.filter(status=status_value)
        if scope:
            queryset = queryset.filter(scope=scope)
        return queryset


class LegalHoldReleaseView(StaffOnlyMixin, APIView):
    def post(self, request, hold_id):
        hold = get_object_or_404(LegalHold, id=hold_id)
        serializer = LegalHoldReleaseSerializer(data=request.data, context={"legal_hold": hold, "request": request})
        serializer.is_valid(raise_exception=True)
        released = serializer.save()
        return Response(LegalHoldSerializer(released).data)


class DataSubjectRequestListCreateView(StaffOnlyMixin, generics.ListCreateAPIView):
    serializer_class = DataSubjectRequestSerializer

    def get_queryset(self):
        queryset = DataSubjectRequest.objects.select_related("user", "organization", "requested_by")
        status_value = self.request.query_params.get("status")
        request_type = self.request.query_params.get("type")
        if status_value:
            queryset = queryset.filter(status=status_value)
        if request_type:
            queryset = queryset.filter(request_type=request_type)
        return queryset


class DataSubjectRequestActionView(StaffOnlyMixin, APIView):
    def post(self, request, request_id):
        record = get_object_or_404(DataSubjectRequest, id=request_id)
        serializer = DataSubjectRequestActionSerializer(data=request.data, context={"request_record": record})
        serializer.is_valid(raise_exception=True)
        updated = serializer.save()
        return Response(DataSubjectRequestSerializer(updated).data)


class RetentionJobListCreateView(StaffOnlyMixin, generics.ListCreateAPIView):
    serializer_class = RetentionJobSerializer
    queryset = RetentionJob.objects.select_related("policy", "created_by")


class RetentionJobPlanView(StaffOnlyMixin, APIView):
    def post(self, request):
        serializer = RetentionJobPlanSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        job = serializer.save()
        return Response(RetentionJobSerializer(job).data, status=status.HTTP_201_CREATED)


class RetentionJobRunView(StaffOnlyMixin, APIView):
    def post(self, request, job_id):
        job = get_object_or_404(RetentionJob, id=job_id)
        serializer = RetentionJobRunSerializer(data=request.data, context={"job": job})
        serializer.is_valid(raise_exception=True)
        updated = serializer.save()
        return Response(RetentionJobSerializer(updated).data)


class AnonymizationRecordListView(StaffOnlyMixin, generics.ListAPIView):
    serializer_class = AnonymizationRecordSerializer
    queryset = AnonymizationRecord.objects.select_related("job", "asset", "performed_by")


class DataInventorySnapshotListView(StaffOnlyMixin, generics.ListAPIView):
    serializer_class = DataInventorySnapshotSerializer
    queryset = DataInventorySnapshot.objects.select_related("generated_by")


class DataInventorySnapshotCreateView(StaffOnlyMixin, APIView):
    def post(self, request):
        serializer = DataInventorySnapshotCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        snapshot = serializer.save()
        return Response(DataInventorySnapshotSerializer(snapshot).data, status=status.HTTP_201_CREATED)
