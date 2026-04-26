from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    DeprovisioningPolicyViewSet,
    DirectoryGroupViewSet,
    DirectoryUserViewSet,
    ScimApplicationViewSet,
    ScimGroupUpsertView,
    ScimProvisioningEventViewSet,
    ScimSummaryView,
    ScimSyncJobViewSet,
    ScimUserDeactivateView,
    ScimUserUpsertView,
)

router = DefaultRouter()
router.register("applications", ScimApplicationViewSet, basename="scim-applications")
router.register("directory-users", DirectoryUserViewSet, basename="scim-directory-users")
router.register("directory-groups", DirectoryGroupViewSet, basename="scim-directory-groups")
router.register("deprovisioning-policies", DeprovisioningPolicyViewSet, basename="scim-deprovisioning-policies")
router.register("sync-jobs", ScimSyncJobViewSet, basename="scim-sync-jobs")
router.register("events", ScimProvisioningEventViewSet, basename="scim-events")

urlpatterns = [
    path("summary/", ScimSummaryView.as_view(), name="scim-summary"),
    path("v2/<uuid:application_id>/Users/upsert/", ScimUserUpsertView.as_view(), name="scim-user-upsert"),
    path("v2/<uuid:application_id>/Users/deactivate/", ScimUserDeactivateView.as_view(), name="scim-user-deactivate"),
    path("v2/<uuid:application_id>/Groups/upsert/", ScimGroupUpsertView.as_view(), name="scim-group-upsert"),
    *router.urls,
]
