from django.db.models import Count, Q
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Organization, OrganizationMembership
from .models import (
    DeprovisioningPolicy,
    DirectoryGroup,
    DirectoryUser,
    ScimApplication,
    ScimProvisioningEvent,
    ScimSyncJob,
)
from .serializers import (
    DeprovisioningPolicySerializer,
    DirectoryGroupSerializer,
    DirectoryUserSerializer,
    ScimApplicationSerializer,
    ScimGroupUpsertSerializer,
    ScimProvisioningEventSerializer,
    ScimSyncJobSerializer,
    ScimUserDeactivateSerializer,
    ScimUserUpsertSerializer,
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


def _client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    return (forwarded.split(",")[0].strip() if forwarded else request.META.get("REMOTE_ADDR")) or None


def _authenticate_scim_application(request, application_id):
    auth = request.META.get("HTTP_AUTHORIZATION", "")
    token = ""
    if auth.lower().startswith("bearer "):
        token = auth.split(" ", 1)[1].strip()
    token = token or request.META.get("HTTP_X_SCIM_TOKEN", "").strip()
    if not token:
        return None
    try:
        app = ScimApplication.objects.select_related("organization").get(id=application_id, status=ScimApplication.Status.ACTIVE)
    except ScimApplication.DoesNotExist:
        return None
    if app.token_hash != ScimApplication.hash_token(token):
        return None
    app.mark_used()
    return app


def _record_event(request, application, event_type, result=ScimProvisioningEvent.Result.SUCCESS, **kwargs):
    return ScimProvisioningEvent.objects.create(
        organization=application.organization if application else None,
        scim_application=application,
        event_type=event_type,
        result=result,
        ip_address=_client_ip(request),
        user_agent=request.META.get("HTTP_USER_AGENT", ""),
        **kwargs,
    )


class ScimSummaryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        orgs = _managed_orgs(request.user)
        apps = ScimApplication.objects.filter(organization__in=orgs)
        users = DirectoryUser.objects.filter(organization__in=orgs)
        groups = DirectoryGroup.objects.filter(organization__in=orgs)
        return Response(
            {
                "organizations": orgs.count(),
                "applications_by_status": list(apps.values("status").annotate(count=Count("id"))),
                "directory_users_by_status": list(users.values("status").annotate(count=Count("id"))),
                "directory_groups": groups.count(),
                "recent_events": ScimProvisioningEventSerializer(ScimProvisioningEvent.objects.filter(organization__in=orgs)[:10], many=True).data,
            }
        )


class ScimApplicationViewSet(viewsets.ModelViewSet):
    serializer_class = ScimApplicationSerializer
    permission_classes = [StaffOrOrgAdmin]

    def get_queryset(self):
        return _filter_by_managed_org(ScimApplication.objects.select_related("organization", "created_by"), self.request.user)

    def perform_create(self, serializer):
        obj = serializer.save()
        self.check_object_permissions(self.request, obj)
        _record_event(self.request, obj, ScimProvisioningEvent.EventType.TOKEN_ROTATED, actor=self.request.user, message="Initial SCIM token created.")

    @action(detail=True, methods=["post"], url_path="rotate-token")
    def rotate_token(self, request, pk=None):
        app = self.get_object()
        raw = app.rotate_token()
        _record_event(request, app, ScimProvisioningEvent.EventType.TOKEN_ROTATED, actor=request.user, message="SCIM token rotated by admin.")
        data = ScimApplicationSerializer(app, context={"request": request}).data
        data["raw_token"] = raw
        return Response(data)

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        app = self.get_object()
        if not app.token_hash:
            app.rotate_token()
        app.activate()
        return Response(ScimApplicationSerializer(app, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def revoke(self, request, pk=None):
        app = self.get_object()
        app.revoke()
        return Response(ScimApplicationSerializer(app, context={"request": request}).data)


class DirectoryUserViewSet(viewsets.ModelViewSet):
    serializer_class = DirectoryUserSerializer
    permission_classes = [StaffOrOrgAdmin]

    def get_queryset(self):
        return _filter_by_managed_org(DirectoryUser.objects.select_related("organization", "scim_application", "user"), self.request.user)

    @action(detail=True, methods=["post"])
    def deprovision(self, request, pk=None):
        directory_user = self.get_object()
        directory_user.mark_deprovisioned()
        ScimProvisioningEvent.objects.create(
            organization=directory_user.organization,
            scim_application=directory_user.scim_application,
            actor=request.user,
            directory_user=directory_user,
            event_type=ScimProvisioningEvent.EventType.USER_DEACTIVATED,
            external_id=directory_user.external_id,
            message="Directory user manually deprovisioned.",
        )
        return Response(DirectoryUserSerializer(directory_user, context={"request": request}).data)


class DirectoryGroupViewSet(viewsets.ModelViewSet):
    serializer_class = DirectoryGroupSerializer
    permission_classes = [StaffOrOrgAdmin]

    def get_queryset(self):
        qs = DirectoryGroup.objects.select_related("organization", "scim_application").annotate(member_count=Count("members"))
        return _filter_by_managed_org(qs, self.request.user)


class DeprovisioningPolicyViewSet(viewsets.ModelViewSet):
    serializer_class = DeprovisioningPolicySerializer
    permission_classes = [StaffOrOrgAdmin]

    def get_queryset(self):
        return _filter_by_managed_org(DeprovisioningPolicy.objects.select_related("organization", "updated_by"), self.request.user)


class ScimSyncJobViewSet(viewsets.ModelViewSet):
    serializer_class = ScimSyncJobSerializer
    permission_classes = [StaffOrOrgAdmin]

    def get_queryset(self):
        return _filter_by_managed_org(ScimSyncJob.objects.select_related("organization", "scim_application", "requested_by"), self.request.user)

    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        job = self.get_object()
        job.mark_running()
        ScimProvisioningEvent.objects.create(
            organization=job.organization,
            scim_application=job.scim_application,
            actor=request.user,
            event_type=ScimProvisioningEvent.EventType.SYNC_STARTED,
            message=f"SCIM sync job started in {job.mode} mode.",
        )
        return Response(ScimSyncJobSerializer(job, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        job = self.get_object()
        job.mark_completed()
        ScimProvisioningEvent.objects.create(
            organization=job.organization,
            scim_application=job.scim_application,
            actor=request.user,
            event_type=ScimProvisioningEvent.EventType.SYNC_COMPLETED,
            payload={"users_seen": job.users_seen, "groups_seen": job.groups_seen},
        )
        return Response(ScimSyncJobSerializer(job, context={"request": request}).data)


class ScimProvisioningEventViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ScimProvisioningEventSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = ScimProvisioningEvent.objects.select_related("organization", "scim_application", "actor", "directory_user", "directory_group")
        if self.request.user.is_staff:
            return qs
        return qs.filter(Q(actor=self.request.user) | Q(organization__in=_managed_orgs(self.request.user))).distinct()


class ScimUserUpsertView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, application_id):
        app = _authenticate_scim_application(request, application_id)
        if not app:
            return Response({"detail": "Invalid SCIM credentials."}, status=status.HTTP_401_UNAUTHORIZED)
        serializer = ScimUserUpsertSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        directory_user, created = serializer.save(application=app)
        _record_event(
            request,
            app,
            ScimProvisioningEvent.EventType.USER_CREATED if created else ScimProvisioningEvent.EventType.USER_UPDATED,
            directory_user=directory_user,
            external_id=directory_user.external_id,
            payload=request.data,
        )
        return Response(DirectoryUserSerializer(directory_user).data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class ScimUserDeactivateView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, application_id):
        app = _authenticate_scim_application(request, application_id)
        if not app:
            return Response({"detail": "Invalid SCIM credentials."}, status=status.HTTP_401_UNAUTHORIZED)
        serializer = ScimUserDeactivateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        directory_user = serializer.save(application=app)
        _record_event(
            request,
            app,
            ScimProvisioningEvent.EventType.USER_DEACTIVATED,
            directory_user=directory_user,
            external_id=directory_user.external_id,
            message=serializer.validated_data.get("reason", ""),
        )
        return Response(DirectoryUserSerializer(directory_user).data)


class ScimGroupUpsertView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, application_id):
        app = _authenticate_scim_application(request, application_id)
        if not app:
            return Response({"detail": "Invalid SCIM credentials."}, status=status.HTTP_401_UNAUTHORIZED)
        serializer = ScimGroupUpsertSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        group, created = serializer.save(application=app)
        _record_event(
            request,
            app,
            ScimProvisioningEvent.EventType.GROUP_CREATED if created else ScimProvisioningEvent.EventType.GROUP_UPDATED,
            directory_group=group,
            external_id=group.external_id,
            payload={"linked_member_count": getattr(group, "linked_member_count", 0)},
        )
        return Response(DirectoryGroupSerializer(group).data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
