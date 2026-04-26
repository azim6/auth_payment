from django.urls import path

from . import views

urlpatterns = [
    path("readiness/", views.NotificationReadinessView.as_view(), name="notification-readiness"),
    path("providers/", views.NotificationProviderListCreateView.as_view(), name="notification-providers"),
    path("templates/", views.NotificationTemplateListCreateView.as_view(), name="notification-templates"),
    path("preferences/", views.NotificationPreferenceListCreateView.as_view(), name="notification-preferences"),
    path("preferences/<uuid:pk>/", views.NotificationPreferenceDetailView.as_view(), name="notification-preference-detail"),
    path("push-tokens/", views.DevicePushTokenListCreateView.as_view(), name="notification-push-tokens"),
    path("push-tokens/<uuid:token_id>/revoke/", views.DevicePushTokenRevokeView.as_view(), name="notification-push-token-revoke"),
    path("events/", views.NotificationEventListCreateView.as_view(), name="notification-events"),
    path("events/<uuid:event_id>/dispatch/", views.NotificationEventDispatchView.as_view(), name="notification-event-dispatch"),
    path("deliveries/", views.NotificationDeliveryListView.as_view(), name="notification-deliveries"),
    path("deliveries/<uuid:delivery_id>/dispatch/", views.NotificationDeliveryDispatchView.as_view(), name="notification-delivery-dispatch"),
    path("suppressions/", views.NotificationSuppressionListCreateView.as_view(), name="notification-suppressions"),
    path("orgs/<slug:org_slug>/summary/", views.NotificationOrgSummaryView.as_view(), name="notification-org-summary"),
]
