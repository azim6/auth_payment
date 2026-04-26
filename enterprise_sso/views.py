from django.db.models import Count, Q
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Organization, OrganizationMembership
from .models import EnterpriseIdentityProvider, JitProvisioningRule, SsoLoginEvent, SsoPolicy, VerifiedDomain
from .serializers import (
    EnterpriseIdentityProviderSerializer,
    JitProvisioningRuleSerializer,
    SsoLoginEventSerializer,
    SsoPolicySerializer,
    SsoRoutingSerializer,
    SsoTestSerializer,
    VerifiedDomainSerializer,
)


class StaffOrOrgAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        org = getattr(obj, "organization", None) or obj
        return OrganizationMembership.objects.filter(
            user=request.user,
            organization=org,
            is_active=True,
            role__in=[OrganizationMembership.Role.OWNER, OrganizationMembership.Role.ADMIN],
        ).exists()


def _managed_orgs(user):
    if user.is_staff:
        return Organization.objects.all()
    return Organization.objects.filter(
        memberships__user=user,
        memberships__is_active=True,
        memberships__role__in=[OrganizationMembership.Role.OWNER, OrganizationMembership.Role.ADMIN],
    ).distinct()


def _filter_by_managed_org(qs, user):
    if user.is_staff:
        return qs
    return qs.filter(organization__in=_managed_orgs(user))


class EnterpriseSsoSummaryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        orgs = _managed_orgs(request.user)
        idps = EnterpriseIdentityProvider.objects.filter(organization__in=orgs)
        domains = VerifiedDomain.objects.filter(organization__in=orgs)
        policies = SsoPolicy.objects.filter(organization__in=orgs)
        return Response(
            {
                "organizations": orgs.count(),
                "identity_providers_by_status": list(idps.values("status").annotate(count=Count("id"))),
                "verified_domains_by_status": list(domains.values("status").annotate(count=Count("id"))),
                "sso_policies": policies.count(),
                "recent_events": SsoLoginEventSerializer(SsoLoginEvent.objects.filter(organization__in=orgs)[:10], many=True).data,
            }
        )


class EnterpriseIdentityProviderViewSet(viewsets.ModelViewSet):
    serializer_class = EnterpriseIdentityProviderSerializer
    permission_classes = [StaffOrOrgAdmin]

    def get_queryset(self):
        return _filter_by_managed_org(EnterpriseIdentityProvider.objects.select_related("organization", "created_by"), self.request.user)

    def perform_create(self, serializer):
        obj = serializer.save()
        self.check_object_permissions(self.request, obj)

    @action(detail=True, methods=["post"])
    def test(self, request, pk=None):
        provider = self.get_object()
        serializer = SsoTestSerializer(data=request.data, context={"request": request, "provider": provider})
        serializer.is_valid(raise_exception=True)
        event = serializer.save()
        return Response(SsoLoginEventSerializer(event).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        provider = self.get_object()
        if not provider.entity_id and not provider.oidc_issuer:
            return Response({"detail": "Configure SAML entity_id or OIDC issuer before activation."}, status=status.HTTP_400_BAD_REQUEST)
        provider.activate()
        return Response(EnterpriseIdentityProviderSerializer(provider).data)

    @action(detail=True, methods=["post"])
    def disable(self, request, pk=None):
        provider = self.get_object()
        provider.disable()
        return Response(EnterpriseIdentityProviderSerializer(provider).data)

    @action(detail=True, methods=["get"], url_path="saml-metadata")
    def saml_metadata(self, request, pk=None):
        provider = self.get_object()
        return Response(
            {
                "organization": provider.organization.slug,
                "provider": provider.slug,
                "acs_url": f"/api/v1/enterprise-sso/saml/{provider.id}/acs/",
                "metadata_url": f"/api/v1/enterprise-sso/idps/{provider.id}/saml-metadata/",
                "entity_id": f"urn:django-auth-platform:{provider.organization.slug}:{provider.slug}",
                "note": "Placeholder metadata. Connect to a vetted SAML toolkit before production federation.",
            }
        )


class VerifiedDomainViewSet(viewsets.ModelViewSet):
    serializer_class = VerifiedDomainSerializer
    permission_classes = [StaffOrOrgAdmin]

    def get_queryset(self):
        return _filter_by_managed_org(VerifiedDomain.objects.select_related("organization", "verified_by"), self.request.user)

    def perform_create(self, serializer):
        obj = serializer.save()
        self.check_object_permissions(self.request, obj)

    @action(detail=True, methods=["post"])
    def check(self, request, pk=None):
        domain = self.get_object()
        domain.last_checked_at = domain.last_checked_at or domain.created_at
        domain.save(update_fields=["last_checked_at", "updated_at"])
        return Response(VerifiedDomainSerializer(domain).data)

    @action(detail=True, methods=["post"])
    def mark_verified(self, request, pk=None):
        domain = self.get_object()
        if not request.user.is_staff:
            return Response({"detail": "Only staff can manually verify a domain."}, status=status.HTTP_403_FORBIDDEN)
        domain.mark_verified(user=request.user)
        return Response(VerifiedDomainSerializer(domain).data)


class SsoPolicyViewSet(viewsets.ModelViewSet):
    serializer_class = SsoPolicySerializer
    permission_classes = [StaffOrOrgAdmin]

    def get_queryset(self):
        return _filter_by_managed_org(SsoPolicy.objects.select_related("organization", "default_identity_provider", "updated_by"), self.request.user)

    def perform_create(self, serializer):
        obj = serializer.save()
        self.check_object_permissions(self.request, obj)


class JitProvisioningRuleViewSet(viewsets.ModelViewSet):
    serializer_class = JitProvisioningRuleSerializer
    permission_classes = [StaffOrOrgAdmin]

    def get_queryset(self):
        return _filter_by_managed_org(JitProvisioningRule.objects.select_related("organization", "identity_provider"), self.request.user)

    def perform_create(self, serializer):
        obj = serializer.save()
        self.check_object_permissions(self.request, obj)


class SsoLoginEventViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SsoLoginEventSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = SsoLoginEvent.objects.select_related("organization", "identity_provider", "user")
        if self.request.user.is_staff:
            return qs
        return qs.filter(Q(user=self.request.user) | Q(organization__in=_managed_orgs(self.request.user))).distinct()


class SsoRoutingView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = SsoRoutingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        domain_part = email.split("@", 1)[1]
        verified = VerifiedDomain.objects.filter(domain__iexact=domain_part, status=VerifiedDomain.Status.VERIFIED).select_related("organization").first()
        if not verified:
            return Response({"email": email, "domain": domain_part, "organization": None, "sso_required": False, "identity_provider": None, "reason": "domain_not_verified"})
        policy = SsoPolicy.objects.filter(organization=verified.organization).select_related("default_identity_provider").first()
        provider = policy.default_identity_provider if policy else None
        required = bool(policy and policy.enforcement in {SsoPolicy.Enforcement.REQUIRED_FOR_DOMAIN, SsoPolicy.Enforcement.REQUIRED_FOR_ALL} and provider and provider.status == EnterpriseIdentityProvider.Status.ACTIVE)
        return Response(
            {
                "email": email,
                "domain": domain_part,
                "organization": verified.organization.slug,
                "sso_required": required,
                "identity_provider": {"id": str(provider.id), "name": provider.name, "protocol": provider.protocol} if provider else None,
                "reason": "sso_required" if required else "sso_optional_or_provider_inactive",
            }
        )
