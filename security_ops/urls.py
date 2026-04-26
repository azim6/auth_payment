from django.urls import path

from .views import (
    AccountRestrictionLiftView,
    AccountRestrictionListCreateView,
    SecurityIncidentDetailView,
    SecurityIncidentListCreateView,
    SecurityRiskEventActionView,
    SecurityRiskEventListCreateView,
    UserSecurityStateView,
)

urlpatterns = [
    path("risk-events/", SecurityRiskEventListCreateView.as_view(), name="security-risk-events"),
    path("risk-events/<uuid:event_id>/action/", SecurityRiskEventActionView.as_view(), name="security-risk-event-action"),
    path("restrictions/", AccountRestrictionListCreateView.as_view(), name="security-account-restrictions"),
    path("restrictions/<uuid:restriction_id>/lift/", AccountRestrictionLiftView.as_view(), name="security-account-restriction-lift"),
    path("incidents/", SecurityIncidentListCreateView.as_view(), name="security-incidents"),
    path("incidents/<uuid:incident_id>/", SecurityIncidentDetailView.as_view(), name="security-incident-detail"),
    path("users/state/", UserSecurityStateView.as_view(), name="security-user-state"),
]
