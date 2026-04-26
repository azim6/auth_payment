from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from admin_integration.permissions import ADMIN_SERVICE_AUTHENTICATION_CLASSES, StaffOrAdminServiceScope
from .models import AccountRestriction, SecurityIncident, SecurityRiskEvent
from .serializers import (
    AccountRestrictionLiftSerializer,
    AccountRestrictionSerializer,
    SecurityIncidentSerializer,
    SecurityRiskEventActionSerializer,
    SecurityRiskEventSerializer,
    UserSecurityStateSerializer,
)


class StaffOnlyMixin:
    permission_classes = [permissions.IsAdminUser]


class SecurityRiskEventListCreateView(StaffOnlyMixin, generics.ListCreateAPIView):
    serializer_class = SecurityRiskEventSerializer

    def get_queryset(self):
        queryset = SecurityRiskEvent.objects.select_related("user", "organization", "subscription")
        category = self.request.query_params.get("category")
        severity = self.request.query_params.get("severity")
        status_value = self.request.query_params.get("status")
        user_id = self.request.query_params.get("user_id")
        organization_id = self.request.query_params.get("organization_id")
        if category:
            queryset = queryset.filter(category=category)
        if severity:
            queryset = queryset.filter(severity=severity)
        if status_value:
            queryset = queryset.filter(status=status_value)
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        if organization_id:
            queryset = queryset.filter(organization_id=organization_id)
        return queryset


class SecurityRiskEventActionView(StaffOnlyMixin, APIView):
    def post(self, request, event_id):
        event = get_object_or_404(SecurityRiskEvent, id=event_id)
        serializer = SecurityRiskEventActionSerializer(data=request.data, context={"request": request, "event": event})
        serializer.is_valid(raise_for_status=True)
        event = serializer.save()
        return Response(SecurityRiskEventSerializer(event).data)


class AccountRestrictionListCreateView(StaffOnlyMixin, generics.ListCreateAPIView):
    authentication_classes = ADMIN_SERVICE_AUTHENTICATION_CLASSES
    permission_classes = [StaffOrAdminServiceScope]
    required_admin_scopes = ["admin:security:write"]
    serializer_class = AccountRestrictionSerializer

    def get_queryset(self):
        queryset = AccountRestriction.objects.select_related("user", "organization", "created_by", "lifted_by")
        active = self.request.query_params.get("active")
        restriction_type = self.request.query_params.get("restriction_type")
        user_id = self.request.query_params.get("user_id")
        organization_id = self.request.query_params.get("organization_id")
        if restriction_type:
            queryset = queryset.filter(restriction_type=restriction_type)
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        if organization_id:
            queryset = queryset.filter(organization_id=organization_id)
        if active in {"1", "true", "yes"}:
            now = timezone.now()
            queryset = queryset.filter(lifted_at__isnull=True, starts_at__lte=now).filter(
                models_q_expires_active(now)
            )
        return queryset


class AccountRestrictionLiftView(StaffOnlyMixin, APIView):
    authentication_classes = ADMIN_SERVICE_AUTHENTICATION_CLASSES
    permission_classes = [StaffOrAdminServiceScope]
    required_admin_scopes = ["admin:security:write"]

    def post(self, request, restriction_id):
        restriction = get_object_or_404(AccountRestriction, id=restriction_id)
        serializer = AccountRestrictionLiftSerializer(data=request.data, context={"request": request, "restriction": restriction})
        serializer.is_valid(raise_exception=True)
        restriction = serializer.save()
        return Response(AccountRestrictionSerializer(restriction).data)


class SecurityIncidentListCreateView(StaffOnlyMixin, generics.ListCreateAPIView):
    serializer_class = SecurityIncidentSerializer

    def get_queryset(self):
        queryset = SecurityIncident.objects.select_related("owner", "related_user", "related_organization").prefetch_related("risk_events")
        status_value = self.request.query_params.get("status")
        severity = self.request.query_params.get("severity")
        if status_value:
            queryset = queryset.filter(status=status_value)
        if severity:
            queryset = queryset.filter(severity=severity)
        return queryset


class SecurityIncidentDetailView(StaffOnlyMixin, generics.RetrieveUpdateAPIView):
    serializer_class = SecurityIncidentSerializer
    lookup_url_kwarg = "incident_id"
    queryset = SecurityIncident.objects.select_related("owner", "related_user", "related_organization").prefetch_related("risk_events")


class UserSecurityStateView(StaffOnlyMixin, APIView):
    def post(self, request):
        serializer = UserSecurityStateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        payload = serializer.save()
        return Response({
            "user_id": str(payload["user_id"]),
            "organization_id": str(payload["organization_id"]) if payload.get("organization_id") else None,
            "active_restrictions": AccountRestrictionSerializer(payload["active_restrictions"], many=True).data,
            "open_risk_events": SecurityRiskEventSerializer(payload["open_risk_events"], many=True).data,
            "open_incidents": SecurityIncidentSerializer(payload["open_incidents"], many=True).data,
        })


from .services import models_q_expires_active