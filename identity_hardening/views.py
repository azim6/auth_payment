from django.db.models import Count, Q
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AccountRecoveryPolicy, IdentityAssuranceEvent, PasskeyCredential, StepUpPolicy, StepUpSession, TrustedDevice
from .serializers import (
    AccountRecoveryPolicySerializer,
    IdentityAssuranceEventSerializer,
    PasskeyChallengeCreateSerializer,
    PasskeyCredentialSerializer,
    PasskeyRegisterCompleteSerializer,
    StepUpPolicySerializer,
    StepUpSatisfySerializer,
    StepUpSessionSerializer,
    TrustedDeviceCreateSerializer,
    TrustedDeviceSerializer,
)
from .services import has_recent_step_up, record_identity_event


class StaffOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_staff)


class IdentityHardeningSummaryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response(
            {
                "passkeys": PasskeyCredential.objects.filter(user=user).values("status").annotate(count=Count("id")),
                "trusted_devices": TrustedDevice.objects.filter(user=user).values("status").annotate(count=Count("id")),
                "active_step_up_sessions": StepUpSession.objects.filter(user=user, revoked_at__isnull=True).values("trigger").annotate(count=Count("id")),
                "recent_assurance_events": IdentityAssuranceEventSerializer(IdentityAssuranceEvent.objects.filter(user=user)[:10], many=True).data,
            }
        )


class PasskeyCredentialViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff and self.request.query_params.get("all") == "1":
            return PasskeyCredential.objects.select_related("user", "organization")
        return PasskeyCredential.objects.filter(user=self.request.user).select_related("organization")

    def get_serializer_class(self):
        if self.action == "register_complete":
            return PasskeyRegisterCompleteSerializer
        return PasskeyCredentialSerializer

    @action(detail=False, methods=["post"], url_path="register/begin")
    def register_begin(self, request):
        serializer = PasskeyChallengeCreateSerializer(data={**request.data, "purpose": "registration"}, context={"request": request})
        serializer.is_valid(raise_exception=True)
        challenge = serializer.save()
        return Response(serializer.to_representation(challenge), status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path="register/complete")
    def register_complete(self, request):
        serializer = PasskeyRegisterCompleteSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        credential = serializer.save()
        return Response(PasskeyCredentialSerializer(credential).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path="authenticate/begin")
    def authenticate_begin(self, request):
        serializer = PasskeyChallengeCreateSerializer(data={**request.data, "purpose": "authentication"}, context={"request": request})
        serializer.is_valid(raise_exception=True)
        challenge = serializer.save()
        return Response(serializer.to_representation(challenge), status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def revoke(self, request, pk=None):
        credential = self.get_object()
        credential.revoke()
        record_identity_event(user=request.user, organization=credential.organization, event_type="passkey.revoked", result="success", method="passkey", request=request)
        return Response(PasskeyCredentialSerializer(credential).data)


class TrustedDeviceViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff and self.request.query_params.get("all") == "1":
            return TrustedDevice.objects.select_related("user", "organization")
        return TrustedDevice.objects.filter(user=self.request.user).select_related("organization")

    def get_serializer_class(self):
        if self.action == "create":
            return TrustedDeviceCreateSerializer
        return TrustedDeviceSerializer

    @action(detail=True, methods=["post"])
    def revoke(self, request, pk=None):
        device = self.get_object()
        device.revoke()
        record_identity_event(user=request.user, organization=device.organization, event_type="trusted_device.revoked", result="success", method="device", request=request)
        return Response(TrustedDeviceSerializer(device).data)


class StepUpPolicyViewSet(viewsets.ModelViewSet):
    queryset = StepUpPolicy.objects.select_related("organization")
    serializer_class = StepUpPolicySerializer
    permission_classes = [StaffOnly]


class StepUpSessionViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = StepUpSessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff and self.request.query_params.get("all") == "1":
            return StepUpSession.objects.select_related("user", "organization")
        return StepUpSession.objects.filter(user=self.request.user).select_related("organization")

    @action(detail=False, methods=["post"])
    def satisfy(self, request):
        serializer = StepUpSatisfySerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        session = serializer.save()
        return Response(StepUpSessionSerializer(session).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"])
    def check(self, request):
        trigger = request.data.get("trigger")
        required_method = request.data.get("required_method")
        if not trigger:
            return Response({"detail": "trigger is required."}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"trigger": trigger, "satisfied": has_recent_step_up(user=request.user, trigger=trigger, required_method=required_method)})

    @action(detail=True, methods=["post"])
    def revoke(self, request, pk=None):
        session = self.get_object()
        session.revoke()
        return Response(StepUpSessionSerializer(session).data)


class AccountRecoveryPolicyViewSet(viewsets.ModelViewSet):
    serializer_class = AccountRecoveryPolicySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = AccountRecoveryPolicy.objects.select_related("user", "organization")
        if self.request.user.is_staff:
            return qs
        return qs.filter(Q(user=self.request.user) | Q(user__isnull=True, organization__memberships__user=self.request.user)).distinct()

    def perform_create(self, serializer):
        if not self.request.user.is_staff:
            serializer.save(user=self.request.user)
        else:
            serializer.save()


class IdentityAssuranceEventViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = IdentityAssuranceEventSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = IdentityAssuranceEvent.objects.select_related("user", "organization")
        if self.request.user.is_staff:
            return qs
        return qs.filter(user=self.request.user)
