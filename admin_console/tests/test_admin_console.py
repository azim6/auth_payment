import pytest
from django.contrib.auth import get_user_model

from admin_console.models import BulkActionRequest, DashboardWidget, OperatorTask
from admin_console.services import build_dashboard_summary, create_dashboard_snapshot


@pytest.mark.django_db
def test_dashboard_summary_counts_users():
    User = get_user_model()
    User.objects.create_user(email="staff@example.com", password="safe-password-123", is_staff=True)
    summary = build_dashboard_summary()
    assert summary["users"]["total"] == 1
    assert summary["users"]["staff"] == 1


@pytest.mark.django_db
def test_dashboard_snapshot_creation():
    snapshot = create_dashboard_snapshot(name="ops")
    assert snapshot.name == "ops"
    assert "users" in snapshot.payload


@pytest.mark.django_db
def test_operator_task_transitions():
    task = OperatorTask.objects.create(title="Review high-risk checkout", domain=OperatorTask.Domain.BILLING)
    task.mark_started()
    assert task.status == OperatorTask.Status.IN_PROGRESS
    task.mark_done()
    assert task.status == OperatorTask.Status.DONE
    assert task.completed_at is not None


@pytest.mark.django_db
def test_bulk_action_requires_different_approver():
    User = get_user_model()
    requester = User.objects.create_user(email="requester@example.com", password="safe-password-123", is_staff=True)
    approver = User.objects.create_user(email="approver@example.com", password="safe-password-123", is_staff=True)
    bulk = BulkActionRequest.objects.create(action=BulkActionRequest.Action.REVOKE_SESSIONS, reason="Compromised token campaign", requested_by=requester)
    bulk.submit()
    assert bulk.status == BulkActionRequest.Status.PENDING_APPROVAL
    with pytest.raises(ValueError):
        bulk.approve(requester)
    bulk.approve(approver)
    assert bulk.status == BulkActionRequest.Status.APPROVED
    assert bulk.approved_by == approver


@pytest.mark.django_db
def test_dashboard_widget_config_is_separate_from_execution():
    widget = DashboardWidget.objects.create(key="open-risk-events", title="Open risk events", domain=DashboardWidget.Domain.SECURITY, query_config={"model": "security_ops.RiskEvent", "filters": {"status": "open"}})
    assert widget.enabled is True
    assert widget.query_config["filters"]["status"] == "open"
