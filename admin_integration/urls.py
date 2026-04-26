from django.urls import path
from . import views

urlpatterns = [
    path("readiness/", views.AdminIntegrationReadinessView.as_view(), name="admin-integration-readiness"),
    path("credentials/", views.AdminServiceCredentialListCreateView.as_view(), name="admin-service-credentials"),
    path("credentials/<uuid:pk>/rotate/", views.AdminServiceCredentialRotateView.as_view(), name="admin-service-credential-rotate"),
    path("credentials/<uuid:pk>/deactivate/", views.AdminServiceCredentialDeactivateView.as_view(), name="admin-service-credential-deactivate"),
    path("scopes/", views.AdminApiScopeListView.as_view(), name="admin-api-scopes"),
    path("contract/", views.AdminApiContractView.as_view(), name="admin-api-contract"),
    path("request-audits/", views.AdminRequestAuditListView.as_view(), name="admin-request-audits"),
    path("verify-signed-request/", views.VerifySignedAdminRequestView.as_view(), name="admin-verify-signed-request"),
]
