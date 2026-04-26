from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from admin_integration.permissions import ADMIN_SERVICE_AUTHENTICATION_CLASSES, StaffOrAdminServiceScope
from .models import BackupSnapshot, EnvironmentCheck, MaintenanceWindow, ReleaseRecord, RestoreRun, ServiceHealthCheck, StatusIncident
from .serializers import (
    BackupSnapshotSerializer,
    EnvironmentCheckSerializer,
    MaintenanceWindowSerializer,
    ReleaseDeploySerializer,
    ReleaseRecordSerializer,
    RestoreApprovalSerializer,
    RestoreRunSerializer,
    ServiceHealthCheckSerializer,
    StatusIncidentSerializer,
)
from .services import build_production_boot_validation_payload, build_readiness_payload, persist_environment_checks, run_health_checks


class StaffOnlyMixin:
    permission_classes = [permissions.IsAdminUser]


class PublicLivenessView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response({"alive": True})


class StaffReadinessView(StaffOnlyMixin, APIView):
    authentication_classes = ADMIN_SERVICE_AUTHENTICATION_CLASSES
    permission_classes = [StaffOrAdminServiceScope]
    required_admin_scopes = ["admin:readiness"]

    def get(self, request):
        payload = build_readiness_payload()
        http_status = status.HTTP_200_OK if payload["ready"] else status.HTTP_503_SERVICE_UNAVAILABLE
        return Response(payload, status=http_status)


class ProductionBootValidationView(StaffOnlyMixin, APIView):
    authentication_classes = ADMIN_SERVICE_AUTHENTICATION_CLASSES
    permission_classes = [StaffOrAdminServiceScope]
    required_admin_scopes = ["admin:readiness"]

    def get(self, request):
        payload = build_production_boot_validation_payload()
        http_status = status.HTTP_200_OK if payload["ready"] else status.HTTP_503_SERVICE_UNAVAILABLE
        return Response(payload, status=http_status)


class EnvironmentCheckListView(StaffOnlyMixin, generics.ListAPIView):
    serializer_class = EnvironmentCheckSerializer

    def get_queryset(self):
        return EnvironmentCheck.objects.all()


class EnvironmentCheckRefreshView(StaffOnlyMixin, APIView):
    def post(self, request):
        checks = persist_environment_checks()
        return Response(EnvironmentCheckSerializer(checks, many=True).data)


class ServiceHealthCheckListView(StaffOnlyMixin, generics.ListAPIView):
    serializer_class = ServiceHealthCheckSerializer

    def get_queryset(self):
        return ServiceHealthCheck.objects.all()


class ServiceHealthCheckRefreshView(StaffOnlyMixin, APIView):
    def post(self, request):
        checks = run_health_checks()
        return Response(ServiceHealthCheckSerializer(checks, many=True).data)


class MaintenanceWindowListCreateView(StaffOnlyMixin, generics.ListCreateAPIView):
    serializer_class = MaintenanceWindowSerializer

    def get_queryset(self):
        queryset = MaintenanceWindow.objects.select_related("created_by")
        status_value = self.request.query_params.get("status")
        if status_value:
            queryset = queryset.filter(status=status_value)
        return queryset


class MaintenanceWindowDetailView(StaffOnlyMixin, generics.RetrieveUpdateAPIView):
    serializer_class = MaintenanceWindowSerializer
    queryset = MaintenanceWindow.objects.select_related("created_by")
    lookup_url_kwarg = "window_id"


class PublicStatusView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        active_maintenance = MaintenanceWindow.objects.filter(status=MaintenanceWindow.Status.ACTIVE).order_by("starts_at")
        active_incidents = StatusIncident.objects.exclude(state=StatusIncident.State.RESOLVED).order_by("-started_at")
        health = ServiceHealthCheck.objects.all()
        return Response({
            "status": "degraded" if active_incidents.exists() else "operational",
            "services": ServiceHealthCheckSerializer(health, many=True).data,
            "active_maintenance": MaintenanceWindowSerializer(active_maintenance, many=True).data,
            "active_incidents": StatusIncidentSerializer(active_incidents, many=True).data,
        })


class BackupSnapshotListCreateView(StaffOnlyMixin, generics.ListCreateAPIView):
    serializer_class = BackupSnapshotSerializer

    def get_queryset(self):
        queryset = BackupSnapshot.objects.select_related("requested_by")
        status_value = self.request.query_params.get("status")
        if status_value:
            queryset = queryset.filter(status=status_value)
        return queryset


class BackupSnapshotDetailView(StaffOnlyMixin, generics.RetrieveUpdateAPIView):
    serializer_class = BackupSnapshotSerializer
    queryset = BackupSnapshot.objects.select_related("requested_by")
    lookup_url_kwarg = "snapshot_id"


class RestoreRunListCreateView(StaffOnlyMixin, generics.ListCreateAPIView):
    serializer_class = RestoreRunSerializer

    def get_queryset(self):
        queryset = RestoreRun.objects.select_related("backup", "requested_by", "approved_by")
        status_value = self.request.query_params.get("status")
        if status_value:
            queryset = queryset.filter(status=status_value)
        return queryset


class RestoreRunApprovalView(StaffOnlyMixin, APIView):
    def post(self, request, restore_id):
        restore = get_object_or_404(RestoreRun, id=restore_id)
        serializer = RestoreApprovalSerializer(data=request.data, context={"request": request, "restore": restore})
        serializer.is_valid(raise_exception=True)
        restore = serializer.save()
        return Response(RestoreRunSerializer(restore).data)


class StatusIncidentListCreateView(StaffOnlyMixin, generics.ListCreateAPIView):
    serializer_class = StatusIncidentSerializer

    def get_queryset(self):
        queryset = StatusIncident.objects.select_related("created_by")
        state = self.request.query_params.get("state")
        impact = self.request.query_params.get("impact")
        if state:
            queryset = queryset.filter(state=state)
        if impact:
            queryset = queryset.filter(impact=impact)
        return queryset


class StatusIncidentDetailView(StaffOnlyMixin, generics.RetrieveUpdateAPIView):
    serializer_class = StatusIncidentSerializer
    queryset = StatusIncident.objects.select_related("created_by")
    lookup_url_kwarg = "incident_id"


class ReleaseRecordListCreateView(StaffOnlyMixin, generics.ListCreateAPIView):
    serializer_class = ReleaseRecordSerializer

    def get_queryset(self):
        queryset = ReleaseRecord.objects.select_related("deployed_by")
        status_value = self.request.query_params.get("status")
        if status_value:
            queryset = queryset.filter(status=status_value)
        return queryset


class ReleaseDeployView(StaffOnlyMixin, APIView):
    def post(self, request, release_id):
        release = get_object_or_404(ReleaseRecord, id=release_id)
        serializer = ReleaseDeploySerializer(data=request.data, context={"request": request, "release": release})
        serializer.is_valid(raise_exception=True)
        release = serializer.save()
        return Response(ReleaseRecordSerializer(release).data)
