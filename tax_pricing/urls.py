from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CurrencyViewSet, RegionViewSet, ExchangeRateSnapshotViewSet, TaxJurisdictionViewSet,
    TaxRateViewSet, TaxExemptionViewSet, RegionalPriceViewSet, LocalizedInvoiceSettingViewSet,
    PriceResolutionRecordViewSet, PriceResolveView, TaxPricingSummaryView,
)

router = DefaultRouter()
router.register("currencies", CurrencyViewSet)
router.register("regions", RegionViewSet)
router.register("fx-rates", ExchangeRateSnapshotViewSet)
router.register("tax-jurisdictions", TaxJurisdictionViewSet)
router.register("tax-rates", TaxRateViewSet)
router.register("tax-exemptions", TaxExemptionViewSet)
router.register("regional-prices", RegionalPriceViewSet)
router.register("invoice-settings", LocalizedInvoiceSettingViewSet)
router.register("price-resolutions", PriceResolutionRecordViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path("summary/", TaxPricingSummaryView.as_view(), name="tax-pricing-summary"),
    path("resolve-price/", PriceResolveView.as_view(), name="tax-pricing-resolve-price"),
]
