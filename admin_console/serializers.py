from rest_framework import serializers

from .models import (
    AdminNote,
    AdminWorkspacePreference,
    BulkActionRequest,
    DashboardSnapshot,
    DashboardWidget,
    OperatorTask,
    SavedAdminView,
)


class DashboardWidgetSerializer(serializers.ModelSerializer):
    class Meta:
        model = DashboardWidget
        fields = "__all__"
        read_only_fields = ["id", "created_by", "updated_by", "created_at", "updated_at"]


class SavedAdminViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavedAdminView
        fields = "__all__"
        read_only_fields = ["id", "owner", "created_at", "updated_at"]


class OperatorTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = OperatorTask
        fields = "__all__"
        read_only_fields = ["id", "created_by", "started_at", "completed_at", "created_at", "updated_at"]


class BulkActionRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = BulkActionRequest
        fields = "__all__"
        read_only_fields = [
            "id", "requested_by", "approved_by", "approved_at", "started_at", "completed_at", "processed_count", "failed_count", "error_summary", "created_at", "updated_at",
        ]


class AdminNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdminNote
        fields = "__all__"
        read_only_fields = ["id", "author", "created_at", "updated_at"]


class AdminWorkspacePreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdminWorkspacePreference
        fields = "__all__"
        read_only_fields = ["id", "user", "created_at", "updated_at"]


class DashboardSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = DashboardSnapshot
        fields = "__all__"
        read_only_fields = ["id", "generated_by", "generated_at", "created_at"]
