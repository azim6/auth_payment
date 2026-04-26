from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    PortalActivityLogViewSet,
    PortalApiKeyViewSet,
    PortalBillingView,
    PortalOrganizationBookmarkViewSet,
    PortalOrganizationViewSet,
    PortalProfileSettingsView,
    PortalReadinessView,
    PortalSummaryView,
    PortalSupportRequestViewSet,
)

router = DefaultRouter()
router.register("organizations", PortalOrganizationViewSet, basename="portal-organizations")
router.register("bookmarks", PortalOrganizationBookmarkViewSet, basename="portal-bookmarks")
router.register("api-keys", PortalApiKeyViewSet, basename="portal-api-keys")
router.register("support-requests", PortalSupportRequestViewSet, basename="portal-support-requests")
router.register("activity", PortalActivityLogViewSet, basename="portal-activity")

urlpatterns = [
    path("readiness/", PortalReadinessView.as_view(), name="portal-readiness"),
    path("summary/", PortalSummaryView.as_view(), name="portal-summary"),
    path("profile/settings/", PortalProfileSettingsView.as_view(), name="portal-profile-settings"),
    path("billing/", PortalBillingView.as_view(), name="portal-billing"),
]
urlpatterns += router.urls
