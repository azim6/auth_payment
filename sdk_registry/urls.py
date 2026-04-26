from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    IntegrationGuideViewSet,
    SdkCompatibilityMatrixViewSet,
    SdkReleaseViewSet,
    SdkSummaryView,
    SdkTelemetryEventViewSet,
)

router = DefaultRouter()
router.register("releases", SdkReleaseViewSet, basename="sdk-release")
router.register("guides", IntegrationGuideViewSet, basename="integration-guide")
router.register("compatibility", SdkCompatibilityMatrixViewSet, basename="sdk-compatibility")
router.register("telemetry", SdkTelemetryEventViewSet, basename="sdk-telemetry")

urlpatterns = [
    path("summary/", SdkSummaryView.as_view(), name="sdk-summary"),
    *router.urls,
]
