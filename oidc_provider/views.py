from django.db.models import Count
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    OAuthClaimMapping,
    OAuthClientTrustProfile,
    OAuthConsentGrant,
    OAuthScopeDefinition,
    OidcDiscoveryMetadataSnapshot,
    OidcRefreshTokenPolicy,
    OidcSigningKey,
    OidcTokenExchangePolicy,
)
from .serializers import (
    ConsentEvaluationSerializer,
    OAuthClaimMappingSerializer,
    OAuthClientTrustProfileSerializer,
    OAuthConsentGrantSerializer,
    OAuthScopeDefinitionSerializer,
    OidcDiscoveryMetadataSnapshotSerializer,
    OidcRefreshTokenPolicySerializer,
    OidcSigningKeySerializer,
    OidcTokenExchangePolicySerializer,
)
from .services import build_oidc_metadata, create_metadata_snapshot, publishable_jwks


class StaffOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)


class OidcProviderSummaryView(APIView):
    permission_classes = [StaffOnly]

    def get(self, request):
        return Response(
            {
                "signing_keys_by_status": list(OidcSigningKey.objects.values("status").annotate(count=Count("id"))),
                "scopes_by_sensitivity": list(OAuthScopeDefinition.objects.values("sensitivity").annotate(count=Count("id"))),
                "claim_mappings": OAuthClaimMapping.objects.filter(is_active=True).count(),
                "trust_profiles_by_level": list(OAuthClientTrustProfile.objects.values("trust_level").annotate(count=Count("id"))),
                "active_consents": OAuthConsentGrant.objects.filter(status=OAuthConsentGrant.Status.ACTIVE).count(),
                "refresh_policies": OidcRefreshTokenPolicy.objects.count(),
                "token_exchange_policies": OidcTokenExchangePolicy.objects.count(),
                "latest_metadata_snapshot": OidcDiscoveryMetadataSnapshotSerializer(OidcDiscoveryMetadataSnapshot.objects.first()).data if OidcDiscoveryMetadataSnapshot.objects.exists() else None,
            }
        )


class PublicJwksView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response(publishable_jwks())


class HardenedOidcDiscoveryView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response(build_oidc_metadata(request))


class OidcSigningKeyViewSet(viewsets.ModelViewSet):
    serializer_class = OidcSigningKeySerializer
    permission_classes = [StaffOnly]
    queryset = OidcSigningKey.objects.select_related("created_by").all()

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        key = self.get_object()
        key.activate()
        return Response(self.get_serializer(key).data)

    @action(detail=True, methods=["post"], url_path="mark-retiring")
    def mark_retiring(self, request, pk=None):
        key = self.get_object()
        key.mark_retiring()
        return Response(self.get_serializer(key).data)

    @action(detail=True, methods=["post"])
    def retire(self, request, pk=None):
        key = self.get_object()
        key.retire()
        return Response(self.get_serializer(key).data)

    @action(detail=True, methods=["post"])
    def revoke(self, request, pk=None):
        key = self.get_object()
        key.revoke()
        return Response(self.get_serializer(key).data)


class OAuthScopeDefinitionViewSet(viewsets.ModelViewSet):
    serializer_class = OAuthScopeDefinitionSerializer
    permission_classes = [StaffOnly]
    queryset = OAuthScopeDefinition.objects.all()


class OAuthClaimMappingViewSet(viewsets.ModelViewSet):
    serializer_class = OAuthClaimMappingSerializer
    permission_classes = [StaffOnly]
    queryset = OAuthClaimMapping.objects.select_related("scope").all()


class OAuthClientTrustProfileViewSet(viewsets.ModelViewSet):
    serializer_class = OAuthClientTrustProfileSerializer
    permission_classes = [StaffOnly]
    queryset = OAuthClientTrustProfile.objects.select_related("client", "reviewed_by").all()

    @action(detail=True, methods=["post"])
    def review(self, request, pk=None):
        profile = self.get_object()
        profile.mark_reviewed(request.user)
        return Response(self.get_serializer(profile).data)


class OidcRefreshTokenPolicyViewSet(viewsets.ModelViewSet):
    serializer_class = OidcRefreshTokenPolicySerializer
    permission_classes = [StaffOnly]
    queryset = OidcRefreshTokenPolicy.objects.select_related("client").all()


class OAuthConsentGrantViewSet(viewsets.ModelViewSet):
    serializer_class = OAuthConsentGrantSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = OAuthConsentGrant.objects.select_related("user", "client")
        if self.request.user.is_staff:
            return qs
        return qs.filter(user=self.request.user)

    def perform_create(self, serializer):
        if not self.request.user.is_staff:
            serializer.save(user=self.request.user)
        else:
            serializer.save()

    @action(detail=True, methods=["post"])
    def revoke(self, request, pk=None):
        grant = self.get_object()
        if not request.user.is_staff and grant.user_id != request.user.id:
            return Response({"detail": "Cannot revoke another user's consent."}, status=status.HTTP_403_FORBIDDEN)
        grant.revoke()
        return Response(self.get_serializer(grant).data)


class OidcTokenExchangePolicyViewSet(viewsets.ModelViewSet):
    serializer_class = OidcTokenExchangePolicySerializer
    permission_classes = [StaffOnly]
    queryset = OidcTokenExchangePolicy.objects.select_related("client").all()


class OidcDiscoveryMetadataSnapshotViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = OidcDiscoveryMetadataSnapshotSerializer
    permission_classes = [StaffOnly]
    queryset = OidcDiscoveryMetadataSnapshot.objects.select_related("generated_by").all()

    @action(detail=False, methods=["post"])
    def create_snapshot(self, request):
        snapshot = create_metadata_snapshot(request, request.user)
        return Response(self.get_serializer(snapshot).data, status=status.HTTP_201_CREATED)


class ConsentEvaluationView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ConsentEvaluationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        client = serializer.validated_data["client_id"]
        requested_scopes = set(serializer.validated_data["scopes"])
        profile = getattr(client, "trust_profile", None)
        scope_defs = OAuthScopeDefinition.objects.filter(name__in=requested_scopes, is_active=True)
        required_consent = {scope.name for scope in scope_defs if scope.requires_consent}
        if profile and not profile.requires_consent_screen:
            required_consent = set()
        active_grants = OAuthConsentGrant.objects.filter(user=request.user, client=client, status=OAuthConsentGrant.Status.ACTIVE)
        consented_scopes = set()
        now = timezone.now()
        for grant in active_grants:
            if grant.expires_at and grant.expires_at <= now:
                continue
            consented_scopes.update(grant.scopes or [])
        missing_scopes = sorted(required_consent - consented_scopes)
        return Response(
            {
                "client_id": client.client_id,
                "requested_scopes": sorted(requested_scopes),
                "known_scopes": sorted(scope_defs.values_list("name", flat=True)),
                "requires_consent": bool(missing_scopes),
                "missing_scopes": missing_scopes,
                "trust_level": profile.trust_level if profile else "unprofiled",
            }
        )
