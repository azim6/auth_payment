from rest_framework import generics, permissions, response, status, views

from .authentication import AdminServiceAuthentication
from .permissions import ADMIN_SERVICE_AUTHENTICATION_CLASSES, StaffOrAdminServiceScope, request_actor_user
from .models import AdminApiContractEndpoint, AdminApiScope, AdminRequestAudit, AdminServiceCredential
from .serializers import AdminApiContractEndpointSerializer, AdminApiScopeSerializer, AdminRequestAuditSerializer, AdminServiceCredentialCreateSerializer, AdminServiceCredentialSerializer
from .services import build_readiness_snapshot, create_admin_service_credential, rotate_admin_service_credential, seed_admin_integration_catalogues


class StaffOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)


class AdminIntegrationReadinessView(views.APIView):
    authentication_classes = ADMIN_SERVICE_AUTHENTICATION_CLASSES
    permission_classes = [StaffOrAdminServiceScope]
    required_admin_scopes = ["admin:readiness"]
    def get(self, request):
        return response.Response(build_readiness_snapshot(created_by=request_actor_user(request), persist=True))


class AdminServiceCredentialListCreateView(views.APIView):
    permission_classes = [StaffOnly]
    def get(self, request):
        return response.Response(AdminServiceCredentialSerializer(AdminServiceCredential.objects.all(), many=True).data)
    def post(self, request):
        serializer = AdminServiceCredentialCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        credential, api_key, signing_secret = create_admin_service_credential(created_by=request.user, **serializer.validated_data)
        return response.Response({"credential": AdminServiceCredentialSerializer(credential).data, "api_key": api_key, "signing_secret": signing_secret, "warning": "Store these values now. They are returned once."}, status=status.HTTP_201_CREATED)


class AdminServiceCredentialRotateView(views.APIView):
    permission_classes = [StaffOnly]
    def post(self, request, pk):
        credential = generics.get_object_or_404(AdminServiceCredential, pk=pk)
        api_key, signing_secret = rotate_admin_service_credential(credential)
        return response.Response({"credential": AdminServiceCredentialSerializer(credential).data, "api_key": api_key, "signing_secret": signing_secret, "warning": "Store these rotated values now. They are returned once."})


class AdminServiceCredentialDeactivateView(views.APIView):
    permission_classes = [StaffOnly]
    def post(self, request, pk):
        credential = generics.get_object_or_404(AdminServiceCredential, pk=pk)
        credential.is_active = False
        credential.save(update_fields=["is_active", "updated_at"])
        return response.Response(AdminServiceCredentialSerializer(credential).data)


class AdminApiScopeListView(generics.ListAPIView):
    authentication_classes = ADMIN_SERVICE_AUTHENTICATION_CLASSES
    permission_classes = [StaffOrAdminServiceScope]
    required_admin_scopes = ["admin:readiness"]
    serializer_class = AdminApiScopeSerializer
    def get_queryset(self):
        seed_admin_integration_catalogues()
        return AdminApiScope.objects.all()


class AdminApiContractView(generics.ListAPIView):
    authentication_classes = ADMIN_SERVICE_AUTHENTICATION_CLASSES
    permission_classes = [StaffOrAdminServiceScope]
    required_admin_scopes = ["admin:readiness"]
    serializer_class = AdminApiContractEndpointSerializer
    def get_queryset(self):
        seed_admin_integration_catalogues()
        return AdminApiContractEndpoint.objects.filter(enabled=True)


class AdminRequestAuditListView(generics.ListAPIView):
    authentication_classes = ADMIN_SERVICE_AUTHENTICATION_CLASSES
    permission_classes = [StaffOrAdminServiceScope]
    required_admin_scopes = ["admin:audit:read"]
    serializer_class = AdminRequestAuditSerializer
    def get_queryset(self):
        return AdminRequestAudit.objects.all()[:500]


class VerifySignedAdminRequestView(views.APIView):
    authentication_classes = [AdminServiceAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request):
        credential = getattr(request, "admin_service_credential", None)
        return response.Response({"ok": True, "credential_id": str(credential.id) if credential else None, "credential_name": credential.name if credential else None, "scopes": sorted(credential.scope_set) if credential else []})
