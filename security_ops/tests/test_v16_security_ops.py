from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from security_ops.models import AccountRestriction, SecurityRiskEvent


def make_staff():
    return User.objects.create_user(
        email="staff@example.com",
        username="staff",
        password="pass12345",
        is_staff=True,
    )


def make_user():
    return User.objects.create_user(
        email="user@example.com",
        username="user",
        password="pass12345",
    )


def test_staff_can_create_and_acknowledge_risk_event(db):
    staff = make_staff()
    user = make_user()
    client = APIClient()
    client.force_authenticate(staff)

    response = client.post("/api/v1/security/risk-events/", {
        "category": "auth",
        "signal": "auth.failed_login_velocity",
        "score": 80,
        "summary": "Too many failed login attempts from one IP.",
        "user": str(user.id),
        "metadata": {"window_minutes": 10},
    }, format="json")

    assert response.status_code == 201
    assert response.data["severity"] == "high"

    event_id = response.data["id"]
    action_response = client.post(f"/api/v1/security/risk-events/{event_id}/action/", {"action": "acknowledge"}, format="json")
    assert action_response.status_code == 200
    assert action_response.data["status"] == "acknowledged"


def test_staff_can_create_and_lift_account_restriction(db):
    staff = make_staff()
    user = make_user()
    client = APIClient()
    client.force_authenticate(staff)

    response = client.post("/api/v1/security/restrictions/", {
        "user": str(user.id),
        "restriction_type": "billing_block",
        "reason": "Manual review required after repeated payment failures.",
        "starts_at": timezone.now().isoformat(),
    }, format="json")

    assert response.status_code == 201
    restriction_id = response.data["id"]
    restriction = AccountRestriction.objects.get(id=restriction_id)
    assert restriction.is_active is True

    lift_response = client.post(f"/api/v1/security/restrictions/{restriction_id}/lift/", {}, format="json")
    assert lift_response.status_code == 200
    restriction.refresh_from_db()
    assert restriction.is_active is False


def test_user_security_state_reports_open_risk_and_restriction(db):
    staff = make_staff()
    user = make_user()
    AccountRestriction.objects.create(user=user, restriction_type="api_block", reason="test")
    SecurityRiskEvent.objects.create(category="platform", signal="platform.test", score=50, severity="medium", user=user, summary="test")

    client = APIClient()
    client.force_authenticate(staff)
    response = client.post("/api/v1/security/users/state/", {"user_id": str(user.id)}, format="json")

    assert response.status_code == 200
    assert len(response.data["active_restrictions"]) == 1
    assert len(response.data["open_risk_events"]) == 1
