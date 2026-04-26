from django.urls import path

from . import views

urlpatterns = [
    path("live/", views.PublicLivenessView.as_view(), name="ops-live"),
    path("ready/", views.StaffReadinessView.as_view(), name="ops-ready"),
    path("production-validation/", views.ProductionBootValidationView.as_view(), name="ops-production-validation"),
    path("status/", views.PublicStatusView.as_view(), name="ops-public-status"),

    path("environment-checks/", views.EnvironmentCheckListView.as_view(), name="environment-check-list"),
    path("environment-checks/refresh/", views.EnvironmentCheckRefreshView.as_view(), name="environment-check-refresh"),
    path("health-checks/", views.ServiceHealthCheckListView.as_view(), name="health-check-list"),
    path("health-checks/refresh/", views.ServiceHealthCheckRefreshView.as_view(), name="health-check-refresh"),

    path("maintenance-windows/", views.MaintenanceWindowListCreateView.as_view(), name="maintenance-window-list"),
    path("maintenance-windows/<int:window_id>/", views.MaintenanceWindowDetailView.as_view(), name="maintenance-window-detail"),

    path("backups/", views.BackupSnapshotListCreateView.as_view(), name="backup-snapshot-list"),
    path("backups/<int:snapshot_id>/", views.BackupSnapshotDetailView.as_view(), name="backup-snapshot-detail"),
    path("restores/", views.RestoreRunListCreateView.as_view(), name="restore-run-list"),
    path("restores/<int:restore_id>/review/", views.RestoreRunApprovalView.as_view(), name="restore-run-review"),

    path("incidents/", views.StatusIncidentListCreateView.as_view(), name="status-incident-list"),
    path("incidents/<int:incident_id>/", views.StatusIncidentDetailView.as_view(), name="status-incident-detail"),

    path("releases/", views.ReleaseRecordListCreateView.as_view(), name="release-record-list"),
    path("releases/<int:release_id>/deploy/", views.ReleaseDeployView.as_view(), name="release-record-deploy"),
]
