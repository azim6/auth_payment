from django.urls import path

from . import views

urlpatterns = [
    path("summary/", views.GovernanceSummaryView.as_view(), name="data-governance-summary"),
    path("categories/", views.DataCategoryListCreateView.as_view(), name="data-categories"),
    path("categories/<uuid:category_id>/", views.DataCategoryDetailView.as_view(), name="data-category-detail"),
    path("assets/", views.DataAssetListCreateView.as_view(), name="data-assets"),
    path("assets/<uuid:asset_id>/", views.DataAssetDetailView.as_view(), name="data-asset-detail"),
    path("retention-policies/", views.RetentionPolicyListCreateView.as_view(), name="retention-policies"),
    path("retention-policies/<uuid:policy_id>/", views.RetentionPolicyDetailView.as_view(), name="retention-policy-detail"),
    path("legal-holds/", views.LegalHoldListCreateView.as_view(), name="legal-holds"),
    path("legal-holds/<uuid:hold_id>/release/", views.LegalHoldReleaseView.as_view(), name="legal-hold-release"),
    path("subject-requests/", views.DataSubjectRequestListCreateView.as_view(), name="data-subject-requests"),
    path("subject-requests/<uuid:request_id>/action/", views.DataSubjectRequestActionView.as_view(), name="data-subject-request-action"),
    path("retention-jobs/", views.RetentionJobListCreateView.as_view(), name="retention-jobs"),
    path("retention-jobs/plan/", views.RetentionJobPlanView.as_view(), name="retention-job-plan"),
    path("retention-jobs/<uuid:job_id>/run/", views.RetentionJobRunView.as_view(), name="retention-job-run"),
    path("anonymization-records/", views.AnonymizationRecordListView.as_view(), name="anonymization-records"),
    path("inventory-snapshots/", views.DataInventorySnapshotListView.as_view(), name="inventory-snapshots"),
    path("inventory-snapshots/create/", views.DataInventorySnapshotCreateView.as_view(), name="inventory-snapshot-create"),
]
