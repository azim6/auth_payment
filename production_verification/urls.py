from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import FeatureFlagInventoryViewSet, ProductionVerificationView, VerificationSnapshotViewSet

router = DefaultRouter()
router.register("snapshots", VerificationSnapshotViewSet, basename="production-verification-snapshot")
router.register("feature-flags", FeatureFlagInventoryViewSet, basename="production-verification-feature-flag")

urlpatterns = [
    path("verify/", ProductionVerificationView.as_view(), name="production-verification-verify"),
]
urlpatterns += router.urls
