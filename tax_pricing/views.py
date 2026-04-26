from django.shortcuts import get_object_or_404
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from billing.models import Plan
from accounts.models import Organization, User
from .models import (
    Currency, Region, ExchangeRateSnapshot, TaxJurisdiction, TaxRate, TaxExemption,
    RegionalPrice, LocalizedInvoiceSetting, PriceResolutionRecord,
)
from .serializers import (
    CurrencySerializer, RegionSerializer, ExchangeRateSnapshotSerializer, TaxJurisdictionSerializer,
    TaxRateSerializer, TaxExemptionSerializer, RegionalPriceSerializer, LocalizedInvoiceSettingSerializer,
    PriceResolutionRecordSerializer, PriceResolutionRequestSerializer,
)
from .services import resolve_plan_price


class StaffOnlyMixin:
    permission_classes = [permissions.IsAdminUser]


class CurrencyViewSet(StaffOnlyMixin, viewsets.ModelViewSet):
    queryset = Currency.objects.all().order_by("code")
    serializer_class = CurrencySerializer


class RegionViewSet(StaffOnlyMixin, viewsets.ModelViewSet):
    queryset = Region.objects.select_related("currency").all().order_by("code")
    serializer_class = RegionSerializer


class ExchangeRateSnapshotViewSet(StaffOnlyMixin, viewsets.ModelViewSet):
    queryset = ExchangeRateSnapshot.objects.select_related("base_currency", "quote_currency").all().order_by("-effective_at")
    serializer_class = ExchangeRateSnapshotSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class TaxJurisdictionViewSet(StaffOnlyMixin, viewsets.ModelViewSet):
    queryset = TaxJurisdiction.objects.all().order_by("country_code", "code")
    serializer_class = TaxJurisdictionSerializer


class TaxRateViewSet(StaffOnlyMixin, viewsets.ModelViewSet):
    queryset = TaxRate.objects.select_related("jurisdiction").all().order_by("-valid_from")
    serializer_class = TaxRateSerializer


class TaxExemptionViewSet(StaffOnlyMixin, viewsets.ModelViewSet):
    queryset = TaxExemption.objects.select_related("jurisdiction", "organization", "user").all().order_by("-created_at")
    serializer_class = TaxExemptionSerializer

    @action(detail=True, methods=["post"])
    def verify(self, request, pk=None):
        exemption = self.get_object()
        exemption.verified_by = request.user
        from django.utils import timezone
        exemption.verified_at = timezone.now()
        exemption.save(update_fields=["verified_by", "verified_at"])
        return Response(self.get_serializer(exemption).data)


class RegionalPriceViewSet(StaffOnlyMixin, viewsets.ModelViewSet):
    queryset = RegionalPrice.objects.select_related("plan", "region", "currency").all().order_by("plan_id", "region__code")
    serializer_class = RegionalPriceSerializer


class LocalizedInvoiceSettingViewSet(StaffOnlyMixin, viewsets.ModelViewSet):
    queryset = LocalizedInvoiceSetting.objects.select_related("region").all().order_by("region__code")
    serializer_class = LocalizedInvoiceSettingSerializer


class PriceResolutionRecordViewSet(StaffOnlyMixin, viewsets.ReadOnlyModelViewSet):
    queryset = PriceResolutionRecord.objects.select_related("plan", "region", "currency", "organization", "user").all().order_by("-created_at")
    serializer_class = PriceResolutionRecordSerializer


class PriceResolveView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        serializer = PriceResolutionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        plan = get_object_or_404(Plan, id=serializer.validated_data["plan_id"])
        organization = None
        user = None
        if serializer.validated_data.get("organization_id"):
            organization = get_object_or_404(Organization, id=serializer.validated_data["organization_id"])
        if serializer.validated_data.get("user_id"):
            user = get_object_or_404(User, id=serializer.validated_data["user_id"])
        try:
            record = resolve_plan_price(plan, serializer.validated_data["region_code"], organization=organization, user=user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(PriceResolutionRecordSerializer(record).data, status=status.HTTP_201_CREATED)


class TaxPricingSummaryView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        return Response({
            "currencies": Currency.objects.count(),
            "regions": Region.objects.count(),
            "regional_prices": RegionalPrice.objects.count(),
            "tax_jurisdictions": TaxJurisdiction.objects.count(),
            "tax_exemptions": TaxExemption.objects.filter(is_active=True).count(),
            "price_resolutions": PriceResolutionRecord.objects.count(),
        })
