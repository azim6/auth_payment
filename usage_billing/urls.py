from django.urls import path

from .views import (
    CreditApplicationListView,
    CreditGrantListCreateView,
    FinalizeUsageWindowView,
    IngestUsageEventView,
    MeterListCreateView,
    MeterPriceListCreateView,
    OrganizationUsageBillingSummaryView,
    PlanUsageWindowView,
    RatedUsageLineListView,
    RateUsageWindowView,
    RunUsageReconciliationView,
    UsageEventListView,
    UsageReconciliationRunListCreateView,
    UsageWindowListView,
)

urlpatterns = [
    path("meters/", MeterListCreateView.as_view(), name="usage-billing-meters"),
    path("meter-prices/", MeterPriceListCreateView.as_view(), name="usage-billing-meter-prices"),
    path("events/", UsageEventListView.as_view(), name="usage-billing-events"),
    path("events/ingest/", IngestUsageEventView.as_view(), name="usage-billing-ingest"),
    path("windows/", UsageWindowListView.as_view(), name="usage-billing-windows"),
    path("windows/plan/", PlanUsageWindowView.as_view(), name="usage-billing-plan-window"),
    path("windows/<uuid:pk>/finalize/", FinalizeUsageWindowView.as_view(), name="usage-billing-finalize-window"),
    path("rated-lines/", RatedUsageLineListView.as_view(), name="usage-billing-rated-lines"),
    path("rated-lines/rate/", RateUsageWindowView.as_view(), name="usage-billing-rate-window"),
    path("credits/", CreditGrantListCreateView.as_view(), name="usage-billing-credits"),
    path("credit-applications/", CreditApplicationListView.as_view(), name="usage-billing-credit-applications"),
    path("reconciliations/", UsageReconciliationRunListCreateView.as_view(), name="usage-billing-reconciliations"),
    path("reconciliations/run/", RunUsageReconciliationView.as_view(), name="usage-billing-run-reconciliation"),
    path("orgs/<slug:slug>/summary/", OrganizationUsageBillingSummaryView.as_view(), name="usage-billing-org-summary"),
]
