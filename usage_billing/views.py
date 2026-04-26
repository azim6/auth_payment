from django.db.models import Sum
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Organization
from billing.models import Subscription
from .models import CreditApplication, CreditGrant, Meter, MeterPrice, RatedUsageLine, UsageAggregationWindow, UsageEvent, UsageReconciliationRun
from .serializers import (
    CreditApplicationSerializer,
    CreditGrantSerializer,
    MeterPriceSerializer,
    MeterSerializer,
    RatedUsageLineSerializer,
    RateUsageWindowSerializer,
    UsageAggregationWindowSerializer,
    UsageEventSerializer,
    UsageIngestSerializer,
    UsageReconciliationRunSerializer,
    UsageWindowPlanSerializer,
)
from .services import aggregate_window, create_reconciliation_run, ingest_usage_event, rate_usage_window


class StaffOnlyMixin:
    permission_classes = [permissions.IsAdminUser]


class MeterListCreateView(StaffOnlyMixin, generics.ListCreateAPIView):
    queryset = Meter.objects.all()
    serializer_class = MeterSerializer


class MeterPriceListCreateView(StaffOnlyMixin, generics.ListCreateAPIView):
    queryset = MeterPrice.objects.select_related("meter", "plan", "addon")
    serializer_class = MeterPriceSerializer


class UsageEventListView(StaffOnlyMixin, generics.ListAPIView):
    queryset = UsageEvent.objects.select_related("organization", "meter", "subscription")
    serializer_class = UsageEventSerializer


class IngestUsageEventView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = UsageIngestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        event = ingest_usage_event(user=request.user, **serializer.validated_data)
        return Response(UsageEventSerializer(event).data, status=status.HTTP_201_CREATED)


class UsageWindowListView(StaffOnlyMixin, generics.ListAPIView):
    queryset = UsageAggregationWindow.objects.select_related("organization", "subscription", "meter")
    serializer_class = UsageAggregationWindowSerializer


class PlanUsageWindowView(StaffOnlyMixin, APIView):
    def post(self, request):
        serializer = UsageWindowPlanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        subscription = get_object_or_404(Subscription, id=serializer.validated_data["subscription"])
        meter = get_object_or_404(Meter, id=serializer.validated_data["meter"])
        window = aggregate_window(subscription=subscription, meter=meter, window_start=serializer.validated_data["window_start"], window_end=serializer.validated_data["window_end"])
        return Response(UsageAggregationWindowSerializer(window).data)


class FinalizeUsageWindowView(StaffOnlyMixin, APIView):
    def post(self, request, pk):
        window = get_object_or_404(UsageAggregationWindow, pk=pk)
        window.finalize()
        return Response(UsageAggregationWindowSerializer(window).data)


class RatedUsageLineListView(StaffOnlyMixin, generics.ListAPIView):
    queryset = RatedUsageLine.objects.select_related("window", "meter_price")
    serializer_class = RatedUsageLineSerializer


class RateUsageWindowView(StaffOnlyMixin, APIView):
    def post(self, request):
        serializer = RateUsageWindowSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        window = get_object_or_404(UsageAggregationWindow, id=serializer.validated_data["window"])
        meter_price = get_object_or_404(MeterPrice, id=serializer.validated_data["meter_price"])
        line = rate_usage_window(window=window, meter_price=meter_price, apply_credits=serializer.validated_data["apply_credits"])
        return Response(RatedUsageLineSerializer(line).data)


class CreditGrantListCreateView(StaffOnlyMixin, generics.ListCreateAPIView):
    queryset = CreditGrant.objects.select_related("organization", "created_by")
    serializer_class = CreditGrantSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class CreditApplicationListView(StaffOnlyMixin, generics.ListAPIView):
    queryset = CreditApplication.objects.select_related("credit_grant", "rated_line")
    serializer_class = CreditApplicationSerializer


class UsageReconciliationRunListCreateView(StaffOnlyMixin, generics.ListCreateAPIView):
    queryset = UsageReconciliationRun.objects.select_related("organization", "created_by")
    serializer_class = UsageReconciliationRunSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class RunUsageReconciliationView(StaffOnlyMixin, APIView):
    def post(self, request):
        serializer = UsageReconciliationRunSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        organization = serializer.validated_data.get("organization")
        run = create_reconciliation_run(
            provider=serializer.validated_data.get("provider", "stripe"),
            organization=organization,
            window_start=serializer.validated_data["window_start"],
            window_end=serializer.validated_data["window_end"],
            created_by=request.user,
        )
        return Response(UsageReconciliationRunSerializer(run).data, status=status.HTTP_201_CREATED)


class OrganizationUsageBillingSummaryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, slug):
        organization = get_object_or_404(Organization, slug=slug)
        open_windows = UsageAggregationWindow.objects.filter(organization=organization, status=UsageAggregationWindow.Status.OPEN).count()
        finalized_windows = UsageAggregationWindow.objects.filter(organization=organization, status=UsageAggregationWindow.Status.FINALIZED).count()
        ready_rated_lines = RatedUsageLine.objects.filter(window__organization=organization, status=RatedUsageLine.Status.READY).count()
        active_credit_cents = CreditGrant.objects.filter(organization=organization, status=CreditGrant.Status.ACTIVE).aggregate(total=Sum("remaining_amount_cents"))["total"] or 0
        return Response({
            "organization": organization.slug,
            "open_windows": open_windows,
            "finalized_windows": finalized_windows,
            "ready_rated_lines": ready_rated_lines,
            "active_credit_cents": active_credit_cents,
        })
