from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from admin_integration.permissions import ADMIN_SERVICE_AUTHENTICATION_CLASSES, StaffOrAdminServiceScope
from accounts.models import Organization
from .models import (
    AdminNote,
    AdminWorkspacePreference,
    BulkActionRequest,
    DashboardSnapshot,
    DashboardWidget,
    OperatorTask,
    SavedAdminView,
)
from .serializers import (
    AdminNoteSerializer,
    AdminWorkspacePreferenceSerializer,
    BulkActionRequestSerializer,
    DashboardSnapshotSerializer,
    DashboardWidgetSerializer,
    OperatorTaskSerializer,
    SavedAdminViewSerializer,
)
from .services import build_admin_console_readiness, build_dashboard_summary, create_dashboard_snapshot, task_breakdown_for_user


class IsStaffOperator(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)


class AdminConsoleReadinessView(APIView):
    authentication_classes = ADMIN_SERVICE_AUTHENTICATION_CLASSES
    permission_classes = [StaffOrAdminServiceScope]
    required_admin_scopes = ["admin:readiness"]

    def get(self, request):
        return Response(build_admin_console_readiness())


class DashboardSummaryView(APIView):
    permission_classes = [IsStaffOperator]

    def get(self, request):
        return Response(build_dashboard_summary())


class CreateDashboardSnapshotView(APIView):
    permission_classes = [IsStaffOperator]

    def post(self, request):
        snapshot = create_dashboard_snapshot(user=request.user, name=request.data.get("name", "global"))
        return Response(DashboardSnapshotSerializer(snapshot).data, status=status.HTTP_201_CREATED)


class DashboardSnapshotListView(generics.ListAPIView):
    permission_classes = [IsStaffOperator]
    serializer_class = DashboardSnapshotSerializer

    def get_queryset(self):
        return DashboardSnapshot.objects.all()[:100]


class DashboardWidgetListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsStaffOperator]
    serializer_class = DashboardWidgetSerializer
    queryset = DashboardWidget.objects.all()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)


class DashboardWidgetDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsStaffOperator]
    serializer_class = DashboardWidgetSerializer
    lookup_field = "key"
    queryset = DashboardWidget.objects.all()

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class SavedAdminViewListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsStaffOperator]
    serializer_class = SavedAdminViewSerializer

    def get_queryset(self):
        qs = SavedAdminView.objects.filter(owner=self.request.user)
        if self.request.user.is_superuser:
            qs = SavedAdminView.objects.all()
        resource = self.request.query_params.get("resource")
        if resource:
            qs = qs.filter(resource=resource)
        return qs

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class SavedAdminViewDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsStaffOperator]
    serializer_class = SavedAdminViewSerializer

    def get_queryset(self):
        if self.request.user.is_superuser:
            return SavedAdminView.objects.all()
        return SavedAdminView.objects.filter(owner=self.request.user)


class OperatorTaskListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsStaffOperator]
    serializer_class = OperatorTaskSerializer

    def get_queryset(self):
        qs = OperatorTask.objects.select_related("assigned_to", "created_by", "organization")
        status_filter = self.request.query_params.get("status")
        assigned = self.request.query_params.get("assigned")
        if status_filter:
            qs = qs.filter(status=status_filter)
        if assigned == "me":
            qs = qs.filter(assigned_to=self.request.user)
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class OperatorTaskDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsStaffOperator]
    serializer_class = OperatorTaskSerializer
    queryset = OperatorTask.objects.all()


class OperatorTaskActionView(APIView):
    permission_classes = [IsStaffOperator]

    def post(self, request, pk):
        task = get_object_or_404(OperatorTask, pk=pk)
        action = request.data.get("action")
        if action == "start":
            task.mark_started(user=request.user)
        elif action == "done":
            task.mark_done()
        elif action in {OperatorTask.Status.BLOCKED, OperatorTask.Status.CANCELED, OperatorTask.Status.OPEN}:
            task.status = action
            task.save(update_fields=["status", "updated_at"])
        else:
            return Response({"detail": "Unsupported task action."}, status=status.HTTP_400_BAD_REQUEST)
        return Response(OperatorTaskSerializer(task).data)


class MyOperatorWorkspaceView(APIView):
    permission_classes = [IsStaffOperator]

    def get(self, request):
        preferences, _ = AdminWorkspacePreference.objects.get_or_create(user=request.user)
        return Response({
            "preferences": AdminWorkspacePreferenceSerializer(preferences).data,
            "tasks": task_breakdown_for_user(request.user),
        })


class AdminWorkspacePreferenceView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsStaffOperator]
    serializer_class = AdminWorkspacePreferenceSerializer

    def get_object(self):
        obj, _ = AdminWorkspacePreference.objects.get_or_create(user=self.request.user)
        return obj


class BulkActionRequestListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsStaffOperator]
    serializer_class = BulkActionRequestSerializer
    queryset = BulkActionRequest.objects.all()

    def perform_create(self, serializer):
        serializer.save(requested_by=self.request.user)


class BulkActionRequestActionView(APIView):
    permission_classes = [IsStaffOperator]

    def post(self, request, pk):
        bulk = get_object_or_404(BulkActionRequest, pk=pk)
        action = request.data.get("action")
        try:
            if action == "submit":
                bulk.submit()
            elif action == "approve":
                bulk.approve(request.user)
            elif action == "reject":
                bulk.status = BulkActionRequest.Status.REJECTED
                bulk.error_summary = request.data.get("reason", "Rejected by operator.")
                bulk.save(update_fields=["status", "error_summary", "updated_at"])
            elif action == "cancel":
                bulk.status = BulkActionRequest.Status.CANCELED
                bulk.save(update_fields=["status", "updated_at"])
            else:
                return Response({"detail": "Unsupported bulk action transition."}, status=status.HTTP_400_BAD_REQUEST)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(BulkActionRequestSerializer(bulk).data)


class AdminNoteListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsStaffOperator]
    serializer_class = AdminNoteSerializer

    def get_queryset(self):
        qs = AdminNote.objects.all()
        subject_type = self.request.query_params.get("subject_type")
        subject_id = self.request.query_params.get("subject_id")
        if subject_type:
            qs = qs.filter(subject_type=subject_type)
        if subject_id:
            qs = qs.filter(subject_id=subject_id)
        return qs

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class AdminNoteDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsStaffOperator]
    serializer_class = AdminNoteSerializer
    queryset = AdminNote.objects.all()


class UserAdminOverviewView(APIView):
    authentication_classes = ADMIN_SERVICE_AUTHENTICATION_CLASSES
    permission_classes = [StaffOrAdminServiceScope]
    required_admin_scopes = ["admin:read"]

    def get(self, request, user_id):
        User = get_user_model()
        user = get_object_or_404(User, pk=user_id)
        notes = AdminNote.objects.filter(subject_type="user", subject_id=str(user.id))[:10]
        return Response({
            "user": {"id": str(user.id), "email": user.email, "is_active": user.is_active, "is_staff": user.is_staff, "date_joined": user.date_joined},
            "notes": AdminNoteSerializer(notes, many=True).data,
        })


class OrganizationAdminOverviewView(APIView):
    authentication_classes = ADMIN_SERVICE_AUTHENTICATION_CLASSES
    permission_classes = [StaffOrAdminServiceScope]
    required_admin_scopes = ["admin:read"]

    def get(self, request, slug):
        org = get_object_or_404(Organization, slug=slug)
        notes = AdminNote.objects.filter(subject_type="organization", subject_id=str(org.id))[:10]
        return Response({
            "organization": {"id": str(org.id), "slug": org.slug, "name": org.name, "created_at": org.created_at},
            "notes": AdminNoteSerializer(notes, many=True).data,
        })
