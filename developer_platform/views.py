from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Organization

from .models import DeveloperApplication, IntegrationAuditEvent, SDKTokenPolicy, WebhookDelivery, WebhookSubscription
from .serializers import (
    DeveloperApplicationRotateSecretSerializer,
    DeveloperApplicationSerializer,
    IntegrationAuditEventSerializer,
    IntegrationSummarySerializer,
    SDKTokenPolicySerializer,
    WebhookDeliverySerializer,
    WebhookSecretRotateSerializer,
    WebhookSubscriptionSerializer,
)
from .services import rotate_application_secret, rotate_webhook_secret, user_can_manage_platform


class PlatformAccessMixin:
    permission_classes = [permissions.IsAuthenticated]

    def _organization_from_request(self):
        org_id = self.request.data.get("organization") or self.request.query_params.get("organization")
        slug = self.request.query_params.get("org_slug")
        if org_id:
            return get_object_or_404(Organization, id=org_id)
        if slug:
            return get_object_or_404(Organization, slug=slug)
        return None

    def check_org_access(self, organization):
        if not user_can_manage_platform(self.request.user, organization):
            self.permission_denied(self.request, message="You must be an organization owner/admin or staff user to manage platform integrations.")


class DeveloperApplicationListCreateView(PlatformAccessMixin, generics.ListCreateAPIView):
    serializer_class = DeveloperApplicationSerializer

    def get_queryset(self):
        queryset = DeveloperApplication.objects.select_related("organization", "project", "created_by")
        if not self.request.user.is_staff:
            queryset = queryset.filter(organization__memberships__user=self.request.user, organization__memberships__is_active=True, organization__memberships__role__in=["owner", "admin"]).distinct()
        org_slug = self.request.query_params.get("org_slug")
        if org_slug:
            queryset = queryset.filter(organization__slug=org_slug)
        project = self.request.query_params.get("project")
        if project:
            queryset = queryset.filter(project__code=project)
        return queryset

    def perform_create(self, serializer):
        organization = serializer.validated_data["organization"]
        self.check_org_access(organization)
        serializer.save()


class DeveloperApplicationDetailView(PlatformAccessMixin, generics.RetrieveUpdateAPIView):
    serializer_class = DeveloperApplicationSerializer
    queryset = DeveloperApplication.objects.select_related("organization", "project", "created_by")
    lookup_url_kwarg = "application_id"

    def get_object(self):
        obj = super().get_object()
        self.check_org_access(obj.organization)
        return obj


class DeveloperApplicationRotateSecretView(PlatformAccessMixin, APIView):
    def post(self, request, application_id):
        app = get_object_or_404(DeveloperApplication.objects.select_related("organization"), id=application_id)
        self.check_org_access(app.organization)
        raw_secret = rotate_application_secret(application=app, actor=request.user, request=request)
        return Response({"client_id": app.client_id, "raw_client_secret": raw_secret})


class SDKTokenPolicyListCreateView(PlatformAccessMixin, generics.ListCreateAPIView):
    serializer_class = SDKTokenPolicySerializer

    def get_queryset(self):
        queryset = SDKTokenPolicy.objects.select_related("application", "application__organization")
        if not self.request.user.is_staff:
            queryset = queryset.filter(application__organization__memberships__user=self.request.user, application__organization__memberships__is_active=True, application__organization__memberships__role__in=["owner", "admin"]).distinct()
        app_id = self.request.query_params.get("application")
        if app_id:
            queryset = queryset.filter(application_id=app_id)
        return queryset

    def perform_create(self, serializer):
        app = serializer.validated_data["application"]
        self.check_org_access(app.organization)
        serializer.save()


class WebhookSubscriptionListCreateView(PlatformAccessMixin, generics.ListCreateAPIView):
    serializer_class = WebhookSubscriptionSerializer

    def get_queryset(self):
        queryset = WebhookSubscription.objects.select_related("organization", "application", "created_by")
        if not self.request.user.is_staff:
            queryset = queryset.filter(organization__memberships__user=self.request.user, organization__memberships__is_active=True, organization__memberships__role__in=["owner", "admin"]).distinct()
        org_slug = self.request.query_params.get("org_slug")
        if org_slug:
            queryset = queryset.filter(organization__slug=org_slug)
        return queryset

    def perform_create(self, serializer):
        organization = serializer.validated_data["organization"]
        self.check_org_access(organization)
        serializer.save()


class WebhookSubscriptionDetailView(PlatformAccessMixin, generics.RetrieveUpdateAPIView):
    serializer_class = WebhookSubscriptionSerializer
    queryset = WebhookSubscription.objects.select_related("organization", "application", "created_by")
    lookup_url_kwarg = "subscription_id"

    def get_object(self):
        obj = super().get_object()
        self.check_org_access(obj.organization)
        return obj


class WebhookSubscriptionRotateSecretView(PlatformAccessMixin, APIView):
    def post(self, request, subscription_id):
        subscription = get_object_or_404(WebhookSubscription.objects.select_related("organization", "application"), id=subscription_id)
        self.check_org_access(subscription.organization)
        raw_secret = rotate_webhook_secret(subscription=subscription, actor=request.user, request=request)
        return Response({"subscription_id": str(subscription.id), "raw_webhook_secret": raw_secret})


class WebhookDeliveryListView(PlatformAccessMixin, generics.ListAPIView):
    serializer_class = WebhookDeliverySerializer

    def get_queryset(self):
        queryset = WebhookDelivery.objects.select_related("subscription", "subscription__organization")
        if not self.request.user.is_staff:
            queryset = queryset.filter(subscription__organization__memberships__user=self.request.user, subscription__organization__memberships__is_active=True, subscription__organization__memberships__role__in=["owner", "admin"]).distinct()
        subscription_id = self.request.query_params.get("subscription")
        if subscription_id:
            queryset = queryset.filter(subscription_id=subscription_id)
        return queryset


class IntegrationAuditEventListView(PlatformAccessMixin, generics.ListAPIView):
    serializer_class = IntegrationAuditEventSerializer

    def get_queryset(self):
        queryset = IntegrationAuditEvent.objects.select_related("organization", "actor", "application")
        if not self.request.user.is_staff:
            queryset = queryset.filter(organization__memberships__user=self.request.user, organization__memberships__is_active=True, organization__memberships__role__in=["owner", "admin"]).distinct()
        org_slug = self.request.query_params.get("org_slug")
        if org_slug:
            queryset = queryset.filter(organization__slug=org_slug)
        return queryset


class IntegrationSummaryView(PlatformAccessMixin, APIView):
    def get(self, request, org_slug):
        organization = get_object_or_404(Organization, slug=org_slug)
        self.check_org_access(organization)
        payload = {
            "organization": organization.id,
            "slug": organization.slug,
            "applications": DeveloperApplication.objects.filter(organization=organization).count(),
            "active_webhooks": WebhookSubscription.objects.filter(organization=organization, status=WebhookSubscription.Status.ACTIVE).count(),
            "pending_deliveries": WebhookDelivery.objects.filter(subscription__organization=organization, status=WebhookDelivery.Status.PENDING).count(),
            "failed_deliveries": WebhookDelivery.objects.filter(subscription__organization=organization, status__in=[WebhookDelivery.Status.FAILED, WebhookDelivery.Status.DEAD]).count(),
        }
        return Response(IntegrationSummarySerializer(payload).data)
