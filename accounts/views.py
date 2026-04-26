from django.contrib.auth import logout
from django.conf import settings
from django.shortcuts import redirect
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions, status, throttling
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenRefreshView

from admin_integration.permissions import (
    ADMIN_SERVICE_AUTHENTICATION_CLASSES,
    StaffOrAdminServiceScope,
    request_actor_user,
    request_admin_audit_metadata,
)

from .models import AccountDeletionRequest, AuditLog, AuthSessionDevice, DataExportRequest, MfaDevice, OAuthClient, OAuthTokenActivity, PrivacyPreference, RecoveryCode, RefreshTokenFamily, ServiceCredential, User, UserConsent
from .audit import write_audit_event
from .auth_completion import build_auth_readiness_report
from .tenant_completion import build_tenant_authorization_readiness_report
from .serializers import (
    ConfirmEmailSerializer,
    AccountDeletionCancelSerializer,
    AccountDeletionConfirmSerializer,
    AccountDeletionCreateSerializer,
    AccountDeletionRequestSerializer,
    AuditLogSerializer,
    AuthSessionDeviceSerializer,
    DataExportCreateSerializer,
    DataExportPayloadSerializer,
    DataExportRequestSerializer,
    LogoutSerializer,
    MfaConfirmSetupSerializer,
    MfaDisableSerializer,
    MfaRegenerateRecoveryCodesSerializer,
    MfaStartSetupSerializer,
    OAuthAuthorizeSerializer,
    OAuthClientSerializer,
    OAuthTokenActivitySerializer,
    OAuthTokenExchangeSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    PrivacyPreferenceSerializer,
    RegisterSerializer,
    ResendEmailVerificationSerializer,
    RefreshTokenFamilySerializer,
    RevokeAllRefreshTokensSerializer,
    ServiceCredentialRotateSerializer,
    ServiceCredentialSerializer,
    ServiceTokenSerializer,
    SessionLoginSerializer,
    TokenIntrospectionSerializer,
    TokenLoginSerializer,
    TokenRevocationSerializer,
    UserConsentSerializer,
    UserPrivateSerializer,
    UserPublicSerializer,
)


class AuthRateThrottle(throttling.ScopedRateThrottle):
    scope = "auth"


class AuthReadinessView(APIView):
    authentication_classes = ADMIN_SERVICE_AUTHENTICATION_CLASSES
    permission_classes = [StaffOrAdminServiceScope]
    required_admin_scopes = ["admin:readiness"]

    def get(self, request):
        report = build_auth_readiness_report()
        write_audit_event(
            request=request,
            actor=request_actor_user(request),
            category=AuditLog.Category.AUTH,
            action="auth_readiness_checked",
            metadata={"overall_status": report["overall_status"], **request_admin_audit_metadata(request)},
        )
        return Response(report)


class TenantAuthorizationReadinessView(APIView):
    authentication_classes = ADMIN_SERVICE_AUTHENTICATION_CLASSES
    permission_classes = [StaffOrAdminServiceScope]
    required_admin_scopes = ["admin:readiness"]

    def get(self, request):
        report = build_tenant_authorization_readiness_report()
        write_audit_event(
            request=request,
            actor=request_actor_user(request),
            category=AuditLog.Category.ADMIN,
            action="tenant_authorization_readiness_checked",
            metadata={"overall_status": report["overall_status"], **request_admin_audit_metadata(request)},
        )
        return Response(report)


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def health_check(request):
    return Response({"status": "ok", "version": "36.0.0"})


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AuthRateThrottle]

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        return Response(response.data, status=status.HTTP_201_CREATED)


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserPrivateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        User.objects.filter(pk=self.request.user.pk).update(last_seen_at=timezone.now())
        self.request.user.refresh_from_db(fields=["last_seen_at"])
        return self.request.user


class PublicProfileView(generics.RetrieveAPIView):
    serializer_class = UserPublicSerializer
    permission_classes = [permissions.AllowAny]
    lookup_url_kwarg = "user_id"

    def get_object(self):
        return get_object_or_404(User.objects.filter(is_active=True), pk=self.kwargs["user_id"])


class TokenLoginView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AuthRateThrottle]

    def post(self, request):
        serializer = TokenLoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data)


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class SessionLoginView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AuthRateThrottle]

    def post(self, request):
        serializer = SessionLoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.login()
        return Response(UserPrivateSerializer(user).data)


class SessionLogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class SessionStatusView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        if not request.user.is_authenticated:
            return Response({"authenticated": False})
        return Response({"authenticated": True, "user": UserPrivateSerializer(request.user).data})


class ResendEmailVerificationView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AuthRateThrottle]

    def post(self, request):
        serializer = ResendEmailVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.save(), status=status.HTTP_202_ACCEPTED)


class ConfirmEmailView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AuthRateThrottle]

    def post(self, request):
        serializer = ConfirmEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserPrivateSerializer(user).data)


class PasswordResetRequestView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AuthRateThrottle]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.save(), status=status.HTTP_202_ACCEPTED)


class PasswordResetConfirmView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AuthRateThrottle]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Password has been reset."}, status=status.HTTP_200_OK)


class EmailTokenRefreshView(TokenRefreshView):
    throttle_classes = [AuthRateThrottle]


class MfaStatusView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(
            {
                "enabled": MfaDevice.objects.filter(user=request.user, confirmed_at__isnull=False).exists(),
                "recovery_codes_remaining": RecoveryCode.objects.filter(user=request.user, used_at__isnull=True).count(),
            }
        )


class MfaStartSetupView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [AuthRateThrottle]

    def post(self, request):
        serializer = MfaStartSetupSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        return Response(serializer.save(), status=status.HTTP_201_CREATED)


class MfaConfirmSetupView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [AuthRateThrottle]

    def post(self, request):
        serializer = MfaConfirmSetupSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        return Response(serializer.save(), status=status.HTTP_200_OK)


class MfaDisableView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [AuthRateThrottle]

    def post(self, request):
        serializer = MfaDisableSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        return Response(serializer.save(), status=status.HTTP_200_OK)


class MfaRegenerateRecoveryCodesView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [AuthRateThrottle]

    def post(self, request):
        serializer = MfaRegenerateRecoveryCodesSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        return Response(serializer.save(), status=status.HTTP_200_OK)


class OAuthClientListCreateView(generics.ListCreateAPIView):
    serializer_class = OAuthClientSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        return OAuthClient.objects.order_by("name")


class OAuthDiscoveryView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        issuer = settings.OIDC_ISSUER.rstrip("/")
        return Response(
            {
                "issuer": issuer,
                "authorization_endpoint": f"{issuer}/api/v1/oauth/authorize/",
                "token_endpoint": f"{issuer}/api/v1/oauth/token/",
                "jwks_uri": f"{issuer}/api/v1/oauth/jwks/",
                "response_types_supported": ["code"],
                "grant_types_supported": ["authorization_code"],
                "subject_types_supported": ["public"],
                "id_token_signing_alg_values_supported": ["HS256"],
                "scopes_supported": ["openid", "profile", "email", "offline_access"],
                "token_endpoint_auth_methods_supported": ["client_secret_post", "none"],
                "code_challenge_methods_supported": ["plain", "S256"],
            }
        )


class OAuthJwksView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        # v4 signs SimpleJWT tokens with the configured Django/SimpleJWT signing key.
        # For full third-party OIDC federation, replace this with RS256/ES256 keys
        # and publish public JWKs only. The empty set avoids leaking symmetric keys.
        return Response({"keys": []})


class OAuthAuthorizeView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [AuthRateThrottle]

    def get(self, request):
        serializer = OAuthAuthorizeSerializer(data=request.query_params, context={"request": request})
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        if request.query_params.get("format") == "json":
            return Response(result)
        return redirect(result["redirect_to"])

    def post(self, request):
        serializer = OAuthAuthorizeSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        return Response(serializer.save(), status=status.HTTP_201_CREATED)


class OAuthTokenView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AuthRateThrottle]

    def post(self, request):
        serializer = OAuthTokenExchangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.save(), status=status.HTTP_200_OK)



class AuthSessionDeviceListView(generics.ListAPIView):
    serializer_class = AuthSessionDeviceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return AuthSessionDevice.objects.filter(user=self.request.user).order_by("-last_seen_at")


class AuthSessionDeviceRevokeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, device_id):
        device = get_object_or_404(AuthSessionDevice, pk=device_id, user=request.user)
        device.revoke()
        write_audit_event(
            request=request,
            actor=request.user,
            category=AuditLog.Category.AUTH,
            action="session_device.revoked",
            metadata={"device_id": str(device.id)},
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class RefreshTokenFamilyListView(generics.ListAPIView):
    serializer_class = RefreshTokenFamilySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return RefreshTokenFamily.objects.filter(user=self.request.user).order_by("-created_at")


class RevokeAllRefreshTokensView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = RevokeAllRefreshTokensSerializer(data={}, context={"request": request})
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        write_audit_event(
            request=request,
            actor=request.user,
            category=AuditLog.Category.AUTH,
            action="refresh_token_family.revoked_all",
            metadata=result,
        )
        return Response(result, status=status.HTTP_200_OK)


class ServiceCredentialRotateView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, credential_id):
        credential = get_object_or_404(ServiceCredential, pk=credential_id)
        serializer = ServiceCredentialRotateSerializer(data={}, context={"credential": credential})
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        write_audit_event(
            request=request,
            actor=request.user,
            category=AuditLog.Category.SERVICE,
            action="service_credential.rotated",
            metadata={"credential_id": str(credential.id), "key_prefix": result["key_prefix"]},
        )
        return Response(result, status=status.HTTP_200_OK)


class ServiceCredentialDeactivateView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, credential_id):
        credential = get_object_or_404(ServiceCredential, pk=credential_id)
        credential.is_active = False
        credential.save(update_fields=["is_active", "updated_at"])
        write_audit_event(
            request=request,
            actor=request.user,
            category=AuditLog.Category.SERVICE,
            action="service_credential.deactivated",
            metadata={"credential_id": str(credential.id), "key_prefix": credential.key_prefix},
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class AuditLogListView(generics.ListAPIView):
    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        queryset = AuditLog.objects.select_related("actor").order_by("-created_at")
        category = self.request.query_params.get("category")
        action = self.request.query_params.get("action")
        outcome = self.request.query_params.get("outcome")
        client_id = self.request.query_params.get("client_id")
        if category:
            queryset = queryset.filter(category=category)
        if action:
            queryset = queryset.filter(action=action)
        if outcome:
            queryset = queryset.filter(outcome=outcome)
        if client_id:
            queryset = queryset.filter(client_id=client_id)
        return queryset


class OAuthTokenActivityListView(generics.ListAPIView):
    serializer_class = OAuthTokenActivitySerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        queryset = OAuthTokenActivity.objects.select_related("user", "client", "service_credential").order_by("-created_at")
        token_type = self.request.query_params.get("token_type")
        client_id = self.request.query_params.get("client_id")
        active = self.request.query_params.get("active")
        if token_type:
            queryset = queryset.filter(token_type=token_type)
        if client_id:
            queryset = queryset.filter(client__client_id=client_id)
        if active == "true":
            queryset = queryset.filter(revoked_at__isnull=True, expires_at__gt=timezone.now())
        if active == "false":
            queryset = queryset.filter(revoked_at__isnull=False) | queryset.filter(expires_at__lte=timezone.now())
        return queryset


class ServiceCredentialListCreateView(generics.ListCreateAPIView):
    serializer_class = ServiceCredentialSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        return ServiceCredential.objects.order_by("name")

    def perform_create(self, serializer):
        credential = serializer.save()
        write_audit_event(
            request=self.request,
            actor=self.request.user,
            category=AuditLog.Category.SERVICE,
            action="service_credential.created",
            metadata={"credential_id": str(credential.id), "key_prefix": credential.key_prefix},
        )


class ServiceTokenView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AuthRateThrottle]

    def post(self, request):
        serializer = ServiceTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        credential = serializer.validated_data["credential"]
        write_audit_event(
            request=request,
            category=AuditLog.Category.SERVICE,
            action="service_token.issued",
            client_id=credential.key_prefix,
            metadata={"credential_id": str(credential.id), "scope": result.get("scope", "")},
        )
        return Response(result, status=status.HTTP_200_OK)


class TokenIntrospectionView(APIView):
    permission_classes = [permissions.IsAdminUser]
    throttle_classes = [AuthRateThrottle]

    def post(self, request):
        serializer = TokenIntrospectionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        write_audit_event(
            request=request,
            actor=request.user,
            category=AuditLog.Category.OAUTH,
            action="token.introspected",
            outcome=AuditLog.Outcome.SUCCESS if result.get("active") else AuditLog.Outcome.FAILURE,
            client_id=result.get("client_id", ""),
            metadata={"token_type": result.get("token_type", "")},
        )
        return Response(result, status=status.HTTP_200_OK)


class TokenRevocationView(APIView):
    permission_classes = [permissions.IsAdminUser]
    throttle_classes = [AuthRateThrottle]

    def post(self, request):
        serializer = TokenRevocationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        write_audit_event(
            request=request,
            actor=request.user,
            category=AuditLog.Category.OAUTH,
            action="token.revoked",
            outcome=AuditLog.Outcome.SUCCESS if result.get("revoked") else AuditLog.Outcome.FAILURE,
        )
        return Response(result, status=status.HTTP_200_OK)

class PrivacyPreferenceView(generics.RetrieveUpdateAPIView):
    serializer_class = PrivacyPreferenceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        obj, _created = PrivacyPreference.objects.get_or_create(user=self.request.user)
        return obj


class UserConsentListCreateView(generics.ListCreateAPIView):
    serializer_class = UserConsentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return UserConsent.objects.filter(user=self.request.user).order_by("-created_at")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context


class DataExportRequestListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return DataExportRequest.objects.filter(user=self.request.user).order_by("-created_at")

    def get_serializer_class(self):
        if self.request.method == "POST":
            return DataExportCreateSerializer
        return DataExportRequestSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        export = serializer.save()
        return Response(DataExportRequestSerializer(export).data, status=status.HTTP_202_ACCEPTED)


class DataExportPayloadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = DataExportPayloadSerializer(context={"request": request})
        return Response(serializer.save())


class AccountDeletionRequestListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return AccountDeletionRequest.objects.filter(user=self.request.user).order_by("-created_at")

    def get_serializer_class(self):
        if self.request.method == "POST":
            return AccountDeletionCreateSerializer
        return AccountDeletionRequestSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        deletion = serializer.save()
        return Response(AccountDeletionRequestSerializer(deletion).data, status=status.HTTP_202_ACCEPTED)


class AccountDeletionConfirmView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [AuthRateThrottle]

    def post(self, request):
        serializer = AccountDeletionConfirmSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        deletion = serializer.save()
        return Response(AccountDeletionRequestSerializer(deletion).data)


class AccountDeletionCancelView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [AuthRateThrottle]

    def post(self, request):
        serializer = AccountDeletionCancelSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        deletion = serializer.save()
        return Response(AccountDeletionRequestSerializer(deletion).data)



from .models import Organization, OrganizationInvitation, OrganizationMembership, PermissionPolicy, RolePermissionGrant, TenantServiceCredential
from .serializers import (
    OrganizationInvitationAcceptSerializer,
    OrganizationInvitationSerializer,
    OrganizationMembershipSerializer,
    OrganizationMembershipUpdateSerializer,
    OrganizationSerializer,
    TenantServiceCredentialRotateSerializer,
    TenantServiceCredentialSerializer,
    PermissionPolicySerializer,
    RolePermissionGrantSerializer,
    RolePermissionMatrixSerializer,
    AccessCheckSerializer,
    UserPermissionSummarySerializer,
)


def get_active_membership_or_404(user, organization):
    return get_object_or_404(
        OrganizationMembership,
        organization=organization,
        user=user,
        is_active=True,
    )


def get_org_by_slug_or_404(slug):
    return get_object_or_404(Organization.objects.filter(is_active=True), slug=slug)


class OrganizationListCreateView(generics.ListCreateAPIView):
    serializer_class = OrganizationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Organization.objects.filter(
            memberships__user=self.request.user,
            memberships__is_active=True,
            is_active=True,
        ).distinct().order_by("name")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context


class OrganizationDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = OrganizationSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_url_kwarg = "slug"

    def get_object(self):
        organization = get_org_by_slug_or_404(self.kwargs["slug"])
        membership = get_active_membership_or_404(self.request.user, organization)
        if self.request.method in {"PUT", "PATCH"} and not membership.can_manage_billing_or_delete:
            self.permission_denied(self.request, message="Only organization owners can update organization settings.")
        return organization

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context


class OrganizationMembershipListView(generics.ListAPIView):
    serializer_class = OrganizationMembershipSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        organization = get_org_by_slug_or_404(self.kwargs["slug"])
        get_active_membership_or_404(self.request.user, organization)
        return organization.memberships.select_related("user").filter(is_active=True)


class OrganizationMembershipUpdateView(generics.UpdateAPIView):
    serializer_class = OrganizationMembershipUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_url_kwarg = "membership_id"

    def get_object(self):
        organization = get_org_by_slug_or_404(self.kwargs["slug"])
        actor_membership = get_active_membership_or_404(self.request.user, organization)
        if not actor_membership.can_manage_members:
            self.permission_denied(self.request, message="Only organization owners/admins can manage members.")
        target = get_object_or_404(OrganizationMembership, id=self.kwargs["membership_id"], organization=organization)
        if target.role == OrganizationMembership.Role.OWNER and target.user_id != self.request.user.id:
            self.permission_denied(self.request, message="Owner memberships require an explicit owner-transfer workflow.")
        return target

    def perform_update(self, serializer):
        membership = serializer.save()
        write_audit_event(
            request=self.request,
            actor=self.request.user,
            category=AuditLog.Category.ADMIN,
            action="organization.membership.updated",
            subject_user_id=membership.user_id,
            metadata={"organization_id": str(membership.organization_id), "membership_id": str(membership.id)},
        )


class OrganizationInvitationListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        return OrganizationInvitationSerializer

    def get_organization(self):
        organization = get_org_by_slug_or_404(self.kwargs["slug"])
        membership = get_active_membership_or_404(self.request.user, organization)
        if self.request.method == "POST" and not membership.can_manage_members:
            self.permission_denied(self.request, message="Only organization owners/admins can invite members.")
        return organization

    def get_queryset(self):
        organization = self.get_organization()
        return OrganizationInvitation.objects.filter(organization=organization).order_by("-created_at")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        context["organization"] = self.get_organization()
        return context

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        invitation = serializer.save()
        return Response(OrganizationInvitationSerializer(invitation).data, status=status.HTTP_201_CREATED)


class OrganizationInvitationAcceptView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [AuthRateThrottle]

    def post(self, request):
        serializer = OrganizationInvitationAcceptSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        membership = serializer.save()
        return Response(OrganizationMembershipSerializer(membership).data, status=status.HTTP_200_OK)


class TenantServiceCredentialListCreateView(generics.ListCreateAPIView):
    serializer_class = TenantServiceCredentialSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_organization(self):
        organization = get_org_by_slug_or_404(self.kwargs["slug"])
        membership = get_active_membership_or_404(self.request.user, organization)
        if self.request.method == "POST" and not membership.can_manage_members:
            self.permission_denied(self.request, message="Only organization owners/admins can create tenant service credentials.")
        return organization

    def get_queryset(self):
        organization = self.get_organization()
        return TenantServiceCredential.objects.filter(organization=organization).order_by("name")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        context["organization"] = self.get_organization()
        return context

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        credential = serializer.save()
        return Response(TenantServiceCredentialSerializer(credential).data, status=status.HTTP_201_CREATED)


class TenantServiceCredentialRotateView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [AuthRateThrottle]

    def post(self, request, slug, credential_id):
        organization = get_org_by_slug_or_404(slug)
        membership = get_active_membership_or_404(request.user, organization)
        if not membership.can_manage_members:
            self.permission_denied(request, message="Only organization owners/admins can rotate tenant service credentials.")
        credential = get_object_or_404(TenantServiceCredential, id=credential_id, organization=organization)
        serializer = TenantServiceCredentialRotateSerializer(context={"request": request, "credential": credential})
        return Response(serializer.save(), status=status.HTTP_200_OK)


class TenantServiceCredentialDeactivateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, slug, credential_id):
        organization = get_org_by_slug_or_404(slug)
        membership = get_active_membership_or_404(request.user, organization)
        if not membership.can_manage_members:
            self.permission_denied(request, message="Only organization owners/admins can deactivate tenant service credentials.")
        credential = get_object_or_404(TenantServiceCredential, id=credential_id, organization=organization)
        credential.is_active = False
        credential.save(update_fields=["is_active", "updated_at"])
        write_audit_event(
            request=request,
            actor=request.user,
            category=AuditLog.Category.SERVICE,
            action="tenant_service_credential.deactivated",
            metadata={"organization_id": str(organization.id), "credential_id": str(credential.id)},
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


def require_policy_manager(request, organization):
    membership = get_active_membership_or_404(request.user, organization)
    if membership.role not in {OrganizationMembership.Role.OWNER, OrganizationMembership.Role.ADMIN}:
        raise PermissionDenied("Only organization owners/admins can manage authorization policies.")
    return membership


class PermissionCatalogView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from .authorization import list_permission_catalog
        return Response({"permissions": list_permission_catalog()})


class OrganizationPermissionSummaryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, slug):
        organization = get_org_by_slug_or_404(slug)
        get_active_membership_or_404(request.user, organization)
        serializer = UserPermissionSummarySerializer(context={"request": request, "organization": organization})
        return Response(serializer.save())


class OrganizationAccessCheckView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, slug):
        organization = get_org_by_slug_or_404(slug)
        require_policy_manager(request, organization)
        serializer = AccessCheckSerializer(data=request.data, context={"request": request, "organization": organization})
        serializer.is_valid(raise_exception=True)
        return Response(serializer.save())


class PermissionPolicyListCreateView(generics.ListCreateAPIView):
    serializer_class = PermissionPolicySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_organization(self):
        organization = get_org_by_slug_or_404(self.kwargs["slug"])
        if self.request.method == "POST":
            require_policy_manager(self.request, organization)
        else:
            get_active_membership_or_404(self.request.user, organization)
        return organization

    def get_queryset(self):
        return PermissionPolicy.objects.filter(organization=self.get_organization()).order_by("code")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        context["organization"] = self.get_organization()
        return context


class PermissionPolicyDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = PermissionPolicySerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_url_kwarg = "policy_id"

    def get_queryset(self):
        organization = get_org_by_slug_or_404(self.kwargs["slug"])
        if self.request.method in {"PUT", "PATCH", "DELETE"}:
            require_policy_manager(self.request, organization)
        else:
            get_active_membership_or_404(self.request.user, organization)
        return PermissionPolicy.objects.filter(organization=organization)

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=["is_active", "updated_at"])
        write_audit_event(
            request=self.request,
            actor=self.request.user,
            category=AuditLog.Category.ADMIN,
            action="permission_policy.disabled",
            metadata={"organization_id": str(instance.organization_id), "policy_id": str(instance.id), "code": instance.code},
        )


class RolePermissionGrantListCreateView(generics.ListCreateAPIView):
    serializer_class = RolePermissionGrantSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_organization(self):
        organization = get_org_by_slug_or_404(self.kwargs["slug"])
        if self.request.method == "POST":
            require_policy_manager(self.request, organization)
        else:
            get_active_membership_or_404(self.request.user, organization)
        return organization

    def get_queryset(self):
        return RolePermissionGrant.objects.filter(organization=self.get_organization()).select_related("policy").order_by("role", "policy__code")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        context["organization"] = self.get_organization()
        return context


class RolePermissionMatrixView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, slug):
        organization = get_org_by_slug_or_404(slug)
        get_active_membership_or_404(request.user, organization)
        serializer = RolePermissionMatrixSerializer(
            [choice[0] for choice in OrganizationMembership.Role.choices],
            many=True,
            context={"organization": organization},
        )
        return Response({"roles": serializer.data})
