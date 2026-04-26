from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    EnterpriseIdentityProviderViewSet,
    EnterpriseSsoSummaryView,
    JitProvisioningRuleViewSet,
    SsoLoginEventViewSet,
    SsoPolicyViewSet,
    SsoRoutingView,
    VerifiedDomainViewSet,
)

router = DefaultRouter()
router.register("idps", EnterpriseIdentityProviderViewSet, basename="enterprise-sso-idps")
router.register("domains", VerifiedDomainViewSet, basename="enterprise-sso-domains")
router.register("policies", SsoPolicyViewSet, basename="enterprise-sso-policies")
router.register("jit-rules", JitProvisioningRuleViewSet, basename="enterprise-sso-jit-rules")
router.register("events", SsoLoginEventViewSet, basename="enterprise-sso-events")

urlpatterns = [
    path("summary/", EnterpriseSsoSummaryView.as_view(), name="enterprise-sso-summary"),
    path("routing/", SsoRoutingView.as_view(), name="enterprise-sso-routing"),
    *router.urls,
]
