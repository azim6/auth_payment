from django.urls import path

from .views import (
    ActivePolicyListView,
    AdminApprovalRequestListCreateView,
    AdminApprovalReviewView,
    AuditExportListCreateView,
    AuditExportMarkReadyView,
    EvidencePackDetailView,
    EvidencePackListCreateView,
    EvidencePackLockView,
    PolicyDocumentDetailView,
    PolicyDocumentListCreateView,
    PolicyPublishView,
    UserPolicyAcceptanceListCreateView,
)

urlpatterns = [
    path("policies/", PolicyDocumentListCreateView.as_view(), name="compliance-policies"),
    path("policies/active/", ActivePolicyListView.as_view(), name="compliance-active-policies"),
    path("policies/<uuid:policy_id>/", PolicyDocumentDetailView.as_view(), name="compliance-policy-detail"),
    path("policies/<uuid:policy_id>/publish/", PolicyPublishView.as_view(), name="compliance-policy-publish"),
    path("policy-acceptances/", UserPolicyAcceptanceListCreateView.as_view(), name="compliance-policy-acceptances"),
    path("approval-requests/", AdminApprovalRequestListCreateView.as_view(), name="compliance-approval-requests"),
    path("approval-requests/<uuid:approval_id>/review/", AdminApprovalReviewView.as_view(), name="compliance-approval-review"),
    path("audit-exports/", AuditExportListCreateView.as_view(), name="compliance-audit-exports"),
    path("audit-exports/<uuid:export_id>/mark-ready/", AuditExportMarkReadyView.as_view(), name="compliance-audit-export-ready"),
    path("evidence-packs/", EvidencePackListCreateView.as_view(), name="compliance-evidence-packs"),
    path("evidence-packs/<uuid:pack_id>/", EvidencePackDetailView.as_view(), name="compliance-evidence-pack-detail"),
    path("evidence-packs/<uuid:pack_id>/lock/", EvidencePackLockView.as_view(), name="compliance-evidence-pack-lock"),
]
