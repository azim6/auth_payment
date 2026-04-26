from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from admin_integration.permissions import ADMIN_SERVICE_AUTHENTICATION_CLASSES, StaffOrAdminServiceScope
from .models import AlertIncident, AlertRule, ApplicationEvent, MetricSnapshot, SLOSnapshot, ServiceLevelObjective, TraceSample
from .serializers import (
    AlertActionSerializer,
    AlertIncidentSerializer,
    AlertRuleSerializer,
    ApplicationEventSerializer,
    MetricSnapshotSerializer,
    SLOCalculateSerializer,
    SLOSnapshotSerializer,
    ServiceLevelObjectiveSerializer,
    TraceSampleSerializer,
)
from .readiness import build_observability_readiness_report
from .services import build_observability_summary, evaluate_alert_rule


class StaffOnlyMixin:
    permission_classes = [permissions.IsAdminUser]


class ObservabilitySummaryView(StaffOnlyMixin, APIView):
    def get(self, request):
        return Response(build_observability_summary())


class ObservabilityReadinessView(StaffOnlyMixin, APIView):
    authentication_classes = ADMIN_SERVICE_AUTHENTICATION_CLASSES
    permission_classes = [StaffOrAdminServiceScope]
    required_admin_scopes = ["admin:readiness"]

    def get(self, request):
        return Response(build_observability_readiness_report())


class ApplicationEventListCreateView(StaffOnlyMixin, generics.ListCreateAPIView):
    serializer_class = ApplicationEventSerializer

    def get_queryset(self):
        queryset = ApplicationEvent.objects.select_related("organization", "user")
        event_type = self.request.query_params.get("event_type")
        source_app = self.request.query_params.get("source_app")
        severity = self.request.query_params.get("severity")
        if event_type:
            queryset = queryset.filter(event_type=event_type)
        if source_app:
            queryset = queryset.filter(source_app=source_app)
        if severity:
            queryset = queryset.filter(severity=severity)
        return queryset


class MetricSnapshotListCreateView(StaffOnlyMixin, generics.ListCreateAPIView):
    serializer_class = MetricSnapshotSerializer

    def get_queryset(self):
        queryset = MetricSnapshot.objects.all()
        name = self.request.query_params.get("name")
        source_app = self.request.query_params.get("source_app")
        if name:
            queryset = queryset.filter(name=name)
        if source_app:
            queryset = queryset.filter(source_app=source_app)
        return queryset


class TraceSampleListCreateView(StaffOnlyMixin, generics.ListCreateAPIView):
    serializer_class = TraceSampleSerializer

    def get_queryset(self):
        queryset = TraceSample.objects.select_related("organization", "user")
        trace_id = self.request.query_params.get("trace_id")
        status_value = self.request.query_params.get("status")
        if trace_id:
            queryset = queryset.filter(trace_id=trace_id)
        if status_value:
            queryset = queryset.filter(status=status_value)
        return queryset


class SLOListCreateView(StaffOnlyMixin, generics.ListCreateAPIView):
    serializer_class = ServiceLevelObjectiveSerializer
    queryset = ServiceLevelObjective.objects.all()


class SLODetailView(StaffOnlyMixin, generics.RetrieveUpdateAPIView):
    serializer_class = ServiceLevelObjectiveSerializer
    queryset = ServiceLevelObjective.objects.all()
    lookup_url_kwarg = "slo_id"


class SLOCalculateView(StaffOnlyMixin, APIView):
    def post(self, request, slo_id):
        slo = get_object_or_404(ServiceLevelObjective, id=slo_id)
        serializer = SLOCalculateSerializer(data=request.data, context={"slo": slo})
        serializer.is_valid(raise_exception=True)
        snapshot = serializer.save()
        return Response(SLOSnapshotSerializer(snapshot).data, status=status.HTTP_201_CREATED)


class SLOSnapshotListView(StaffOnlyMixin, generics.ListAPIView):
    serializer_class = SLOSnapshotSerializer

    def get_queryset(self):
        queryset = SLOSnapshot.objects.select_related("slo")
        slo_id = self.request.query_params.get("slo")
        if slo_id:
            queryset = queryset.filter(slo_id=slo_id)
        return queryset


class AlertRuleListCreateView(StaffOnlyMixin, generics.ListCreateAPIView):
    serializer_class = AlertRuleSerializer
    queryset = AlertRule.objects.select_related("created_by")


class AlertRuleEvaluateView(StaffOnlyMixin, APIView):
    def post(self, request, rule_id):
        rule = get_object_or_404(AlertRule, id=rule_id)
        incident = evaluate_alert_rule(rule)
        if not incident:
            return Response({"triggered": False})
        return Response({"triggered": True, "incident": AlertIncidentSerializer(incident).data}, status=status.HTTP_201_CREATED)


class AlertIncidentListView(StaffOnlyMixin, generics.ListAPIView):
    serializer_class = AlertIncidentSerializer

    def get_queryset(self):
        queryset = AlertIncident.objects.select_related("rule", "acknowledged_by", "resolved_by")
        state = self.request.query_params.get("state")
        if state:
            queryset = queryset.filter(state=state)
        return queryset


class AlertIncidentActionView(StaffOnlyMixin, APIView):
    def post(self, request, incident_id):
        incident = get_object_or_404(AlertIncident, id=incident_id)
        serializer = AlertActionSerializer(data=request.data, context={"incident": incident, "request": request})
        serializer.is_valid(raise_exception=True)
        incident = serializer.save()
        return Response(AlertIncidentSerializer(incident).data)
