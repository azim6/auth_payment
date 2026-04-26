from django.urls import path

from . import views

urlpatterns = [
    path("readiness/", views.ObservabilityReadinessView.as_view(), name="observability-readiness"),
    path("summary/", views.ObservabilitySummaryView.as_view(), name="observability-summary"),
    path("events/", views.ApplicationEventListCreateView.as_view(), name="observability-events"),
    path("metrics/", views.MetricSnapshotListCreateView.as_view(), name="observability-metrics"),
    path("traces/", views.TraceSampleListCreateView.as_view(), name="observability-traces"),
    path("slos/", views.SLOListCreateView.as_view(), name="observability-slos"),
    path("slos/<uuid:slo_id>/", views.SLODetailView.as_view(), name="observability-slo-detail"),
    path("slos/<uuid:slo_id>/calculate/", views.SLOCalculateView.as_view(), name="observability-slo-calculate"),
    path("slo-snapshots/", views.SLOSnapshotListView.as_view(), name="observability-slo-snapshots"),
    path("alert-rules/", views.AlertRuleListCreateView.as_view(), name="observability-alert-rules"),
    path("alert-rules/<uuid:rule_id>/evaluate/", views.AlertRuleEvaluateView.as_view(), name="observability-alert-evaluate"),
    path("alert-incidents/", views.AlertIncidentListView.as_view(), name="observability-alert-incidents"),
    path("alert-incidents/<uuid:incident_id>/action/", views.AlertIncidentActionView.as_view(), name="observability-alert-action"),
]
