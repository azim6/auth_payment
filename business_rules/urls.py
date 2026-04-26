from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AccessCheckView,
    ProductAccessDecisionListView,
    ProductAccessOverrideViewSet,
    ProductAccessSummaryView,
    ProductCatalogView,
    ProductUsageEventListView,
    ResetUsageView,
)

router = DefaultRouter()
router.register("overrides", ProductAccessOverrideViewSet, basename="business-overrides")

urlpatterns = [
    path("catalog/", ProductCatalogView.as_view(), name="business-product-catalog"),
    path("access-check/", AccessCheckView.as_view(), name="business-access-check"),
    path("access-summary/", ProductAccessSummaryView.as_view(), name="business-access-summary"),
    path("usage-events/", ProductUsageEventListView.as_view(), name="business-usage-events"),
    path("usage-events/reset/", ResetUsageView.as_view(), name="business-reset-usage"),
    path("access-decisions/", ProductAccessDecisionListView.as_view(), name="business-access-decisions"),
    path("", include(router.urls)),
]
