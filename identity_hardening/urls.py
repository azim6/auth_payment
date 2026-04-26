from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    AccountRecoveryPolicyViewSet,
    IdentityAssuranceEventViewSet,
    IdentityHardeningSummaryView,
    PasskeyCredentialViewSet,
    StepUpPolicyViewSet,
    StepUpSessionViewSet,
    TrustedDeviceViewSet,
)

router = DefaultRouter()
router.register("passkeys", PasskeyCredentialViewSet, basename="identity-passkeys")
router.register("trusted-devices", TrustedDeviceViewSet, basename="identity-trusted-devices")
router.register("step-up-policies", StepUpPolicyViewSet, basename="identity-step-up-policies")
router.register("step-up-sessions", StepUpSessionViewSet, basename="identity-step-up-sessions")
router.register("recovery-policies", AccountRecoveryPolicyViewSet, basename="identity-recovery-policies")
router.register("assurance-events", IdentityAssuranceEventViewSet, basename="identity-assurance-events")

urlpatterns = [path("summary/", IdentityHardeningSummaryView.as_view(), name="identity-hardening-summary"), *router.urls]
