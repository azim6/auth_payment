from django.db.models import Count
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from admin_integration.permissions import ADMIN_SERVICE_AUTHENTICATION_CLASSES, StaffOrAdminServiceScope
from accounts.models import Organization

from .models import (
    DevicePushToken,
    NotificationDelivery,
    NotificationEvent,
    NotificationPreference,
    NotificationProvider,
    NotificationSuppression,
    NotificationTemplate,
)
from .serializers import (
    DevicePushTokenSerializer,
    NotificationDeliverySerializer,
    NotificationEventSerializer,
    NotificationPreferenceSerializer,
    NotificationProviderSerializer,
    NotificationSummarySerializer,
    NotificationSuppressionSerializer,
    NotificationTemplateSerializer,
)
from .readiness import build_notification_readiness_report
from .services import dispatch_delivery, enqueue_deliveries


class NotificationAccessMixin:
    permission_classes = [permissions.IsAuthenticated]

    def check_org_admin(self, organization):
        user = self.request.user
        if user.is_staff:
            return
        allowed = organization.memberships.filter(user=user, is_active=True, role__in=["owner", "admin"]).exists()
        if not allowed:
            self.permission_denied(self.request, message="Organization owner/admin access required.")

    def org_admin_queryset(self, queryset, org_field="organization"):
        if self.request.user.is_staff:
            return queryset
        return queryset.filter(**{f"{org_field}__memberships__user": self.request.user, f"{org_field}__memberships__is_active": True, f"{org_field}__memberships__role__in": ["owner", "admin"]}).distinct()


class NotificationProviderListCreateView(NotificationAccessMixin, generics.ListCreateAPIView):
    serializer_class = NotificationProviderSerializer
    permission_classes = [permissions.IsAdminUser]
    queryset = NotificationProvider.objects.all()


class NotificationTemplateListCreateView(NotificationAccessMixin, generics.ListCreateAPIView):
    serializer_class = NotificationTemplateSerializer

    def get_queryset(self):
        qs = NotificationTemplate.objects.select_related("organization", "project", "created_by")
        if self.request.user.is_staff:
            return qs
        return qs.filter(organization__memberships__user=self.request.user, organization__memberships__is_active=True, organization__memberships__role__in=["owner", "admin"]).distinct()

    def perform_create(self, serializer):
        org = serializer.validated_data.get("organization")
        if org:
            self.check_org_admin(org)
        elif not self.request.user.is_staff:
            self.permission_denied(self.request, message="Staff access required for global templates.")
        serializer.save(created_by=self.request.user)


class NotificationPreferenceListCreateView(NotificationAccessMixin, generics.ListCreateAPIView):
    serializer_class = NotificationPreferenceSerializer

    def get_queryset(self):
        return NotificationPreference.objects.filter(user=self.request.user).select_related("organization")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class NotificationPreferenceDetailView(NotificationAccessMixin, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = NotificationPreferenceSerializer

    def get_queryset(self):
        return NotificationPreference.objects.filter(user=self.request.user)


class DevicePushTokenListCreateView(NotificationAccessMixin, generics.ListCreateAPIView):
    serializer_class = DevicePushTokenSerializer

    def get_queryset(self):
        return DevicePushToken.objects.filter(user=self.request.user)


class DevicePushTokenRevokeView(NotificationAccessMixin, APIView):
    def post(self, request, token_id):
        token = get_object_or_404(DevicePushToken, id=token_id, user=request.user)
        token.revoke()
        return Response({"status": "revoked"})


class NotificationEventListCreateView(NotificationAccessMixin, generics.ListCreateAPIView):
    serializer_class = NotificationEventSerializer

    def get_queryset(self):
        qs = NotificationEvent.objects.select_related("organization", "user", "project", "created_by")
        if self.request.user.is_staff:
            return qs
        return qs.filter(organization__memberships__user=self.request.user, organization__memberships__is_active=True, organization__memberships__role__in=["owner", "admin"]).distinct()

    def perform_create(self, serializer):
        org = serializer.validated_data.get("organization")
        if org:
            self.check_org_admin(org)
        elif not self.request.user.is_staff:
            self.permission_denied(self.request, message="Organization is required for non-staff notification events.")
        serializer.save()


class NotificationEventDispatchView(NotificationAccessMixin, APIView):
    def post(self, request, event_id):
        event = get_object_or_404(NotificationEvent.objects.select_related("organization", "user", "project"), id=event_id)
        if event.organization_id:
            self.check_org_admin(event.organization)
        elif not request.user.is_staff:
            self.permission_denied(request, message="Staff access required for global events.")
        channels = request.data.get("channels") or None
        deliveries = enqueue_deliveries(event, channels=channels)
        return Response({"event_id": str(event.id), "deliveries_created": len(deliveries)})


class NotificationDeliveryListView(NotificationAccessMixin, generics.ListAPIView):
    serializer_class = NotificationDeliverySerializer

    def get_queryset(self):
        qs = NotificationDelivery.objects.select_related("event", "event__organization", "template", "provider")
        if self.request.user.is_staff:
            return qs
        return qs.filter(event__organization__memberships__user=self.request.user, event__organization__memberships__is_active=True, event__organization__memberships__role__in=["owner", "admin"]).distinct()


class NotificationDeliveryDispatchView(NotificationAccessMixin, APIView):
    def post(self, request, delivery_id):
        delivery = get_object_or_404(NotificationDelivery.objects.select_related("event", "event__organization", "provider"), id=delivery_id)
        if delivery.event.organization_id:
            self.check_org_admin(delivery.event.organization)
        elif not request.user.is_staff:
            self.permission_denied(request, message="Staff access required for global deliveries.")
        dispatch_delivery(delivery)
        return Response(NotificationDeliverySerializer(delivery).data)


class NotificationSuppressionListCreateView(NotificationAccessMixin, generics.ListCreateAPIView):
    serializer_class = NotificationSuppressionSerializer
    permission_classes = [permissions.IsAdminUser]
    queryset = NotificationSuppression.objects.all()


class NotificationOrgSummaryView(NotificationAccessMixin, APIView):
    def get(self, request, org_slug):
        organization = get_object_or_404(Organization, slug=org_slug)
        self.check_org_admin(organization)
        deliveries = NotificationDelivery.objects.filter(event__organization=organization).values("status").annotate(count=Count("id"))
        by_status = {row["status"]: row["count"] for row in deliveries}
        payload = {
            "organization": organization.id,
            "pending": by_status.get(NotificationDelivery.Status.PENDING, 0),
            "sent": by_status.get(NotificationDelivery.Status.SENT, 0),
            "failed": by_status.get(NotificationDelivery.Status.FAILED, 0),
            "dead": by_status.get(NotificationDelivery.Status.DEAD, 0),
            "templates": NotificationTemplate.objects.filter(organization=organization).count(),
            "active_providers": NotificationProvider.objects.filter(status=NotificationProvider.Status.ACTIVE).count(),
        }
        return Response(NotificationSummarySerializer(payload).data)


class NotificationReadinessView(NotificationAccessMixin, APIView):
    authentication_classes = ADMIN_SERVICE_AUTHENTICATION_CLASSES
    permission_classes = [StaffOrAdminServiceScope]
    required_admin_scopes = ["admin:readiness"]

    def get(self, request):
        return Response(build_notification_readiness_report())
