from django.urls import path

from . import views

urlpatterns = [
    path("applications/", views.DeveloperApplicationListCreateView.as_view(), name="platform-applications"),
    path("applications/<uuid:application_id>/", views.DeveloperApplicationDetailView.as_view(), name="platform-application-detail"),
    path("applications/<uuid:application_id>/rotate-secret/", views.DeveloperApplicationRotateSecretView.as_view(), name="platform-application-rotate-secret"),
    path("sdk-token-policies/", views.SDKTokenPolicyListCreateView.as_view(), name="platform-sdk-token-policies"),
    path("webhooks/subscriptions/", views.WebhookSubscriptionListCreateView.as_view(), name="platform-webhook-subscriptions"),
    path("webhooks/subscriptions/<uuid:subscription_id>/", views.WebhookSubscriptionDetailView.as_view(), name="platform-webhook-subscription-detail"),
    path("webhooks/subscriptions/<uuid:subscription_id>/rotate-secret/", views.WebhookSubscriptionRotateSecretView.as_view(), name="platform-webhook-subscription-rotate-secret"),
    path("webhooks/deliveries/", views.WebhookDeliveryListView.as_view(), name="platform-webhook-deliveries"),
    path("audit-events/", views.IntegrationAuditEventListView.as_view(), name="platform-audit-events"),
    path("orgs/<slug:org_slug>/summary/", views.IntegrationSummaryView.as_view(), name="platform-org-summary"),
]
