from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    ConsentEvaluationView,
    HardenedOidcDiscoveryView,
    OAuthClaimMappingViewSet,
    OAuthClientTrustProfileViewSet,
    OAuthConsentGrantViewSet,
    OAuthScopeDefinitionViewSet,
    OidcDiscoveryMetadataSnapshotViewSet,
    OidcProviderSummaryView,
    OidcRefreshTokenPolicyViewSet,
    OidcSigningKeyViewSet,
    OidcTokenExchangePolicyViewSet,
    PublicJwksView,
)

router = DefaultRouter()
router.register("signing-keys", OidcSigningKeyViewSet, basename="oidc-signing-key")
router.register("scopes", OAuthScopeDefinitionViewSet, basename="oauth-scope")
router.register("claims", OAuthClaimMappingViewSet, basename="oauth-claim")
router.register("trust-profiles", OAuthClientTrustProfileViewSet, basename="oauth-client-trust-profile")
router.register("refresh-token-policies", OidcRefreshTokenPolicyViewSet, basename="oidc-refresh-token-policy")
router.register("consents", OAuthConsentGrantViewSet, basename="oauth-consent")
router.register("token-exchange-policies", OidcTokenExchangePolicyViewSet, basename="oidc-token-exchange-policy")
router.register("metadata-snapshots", OidcDiscoveryMetadataSnapshotViewSet, basename="oidc-metadata-snapshot")

urlpatterns = [
    path("summary/", OidcProviderSummaryView.as_view(), name="oidc-provider-summary"),
    path(".well-known/openid-configuration/", HardenedOidcDiscoveryView.as_view(), name="oidc-provider-discovery"),
    path("jwks/", PublicJwksView.as_view(), name="oidc-jwks"),
    path("consent/evaluate/", ConsentEvaluationView.as_view(), name="oidc-consent-evaluate"),
]
urlpatterns += router.urls
