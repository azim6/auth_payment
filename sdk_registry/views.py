from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import IntegrationGuide, SdkCompatibilityMatrix, SdkRelease, SdkTelemetryEvent
from .serializers import (
    IntegrationGuideSerializer,
    SdkCompatibilityMatrixSerializer,
    SdkReleaseSerializer,
    SdkTelemetryEventSerializer,
)
from .services import sdk_summary


class StaffWritePublicReadPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_staff)


class SdkSummaryView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response(sdk_summary())


class SdkReleaseViewSet(viewsets.ModelViewSet):
    queryset = SdkRelease.objects.all()
    serializer_class = SdkReleaseSerializer
    permission_classes = [StaffWritePublicReadPermission]
    filterset_fields = ["platform", "status"]
    search_fields = ["platform", "version", "release_notes"]
    ordering_fields = ["platform", "version", "published_at", "created_at"]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user if self.request.user.is_authenticated else None)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def publish(self, request, pk=None):
        release = self.get_object()
        release.publish()
        return Response(self.get_serializer(release).data)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def deprecate(self, request, pk=None):
        release = self.get_object()
        release.status = "deprecated"
        release.save(update_fields=["status", "updated_at"])
        return Response(self.get_serializer(release).data)


class IntegrationGuideViewSet(viewsets.ModelViewSet):
    queryset = IntegrationGuide.objects.all()
    serializer_class = IntegrationGuideSerializer
    permission_classes = [StaffWritePublicReadPermission]
    lookup_field = "slug"
    filterset_fields = ["audience", "is_published"]
    search_fields = ["slug", "title", "summary", "content_markdown"]

    def get_queryset(self):
        qs = super().get_queryset()
        if not (self.request.user and self.request.user.is_staff):
            qs = qs.filter(is_published=True)
        return qs


class SdkCompatibilityMatrixViewSet(viewsets.ModelViewSet):
    queryset = SdkCompatibilityMatrix.objects.all()
    serializer_class = SdkCompatibilityMatrixSerializer
    permission_classes = [StaffWritePublicReadPermission]
    filterset_fields = ["sdk_platform", "api_version"]
    search_fields = ["sdk_platform", "sdk_version", "notes"]


class SdkTelemetryEventViewSet(viewsets.ModelViewSet):
    queryset = SdkTelemetryEvent.objects.all()
    serializer_class = SdkTelemetryEventSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]
    filterset_fields = ["platform", "sdk_version", "event_type", "application_id"]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)
