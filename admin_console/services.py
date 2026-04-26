from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.utils import timezone

from accounts.models import Organization
from .models import DashboardSnapshot, OperatorTask, BulkActionRequest


def _safe_count(model, **filters):
    try:
        return model.objects.filter(**filters).count()
    except Exception:
        return None


def build_dashboard_summary():
    """Return a compact, provider-neutral operations summary for admin dashboards."""
    User = get_user_model()
    data = {
        "generated_at": timezone.now().isoformat(),
        "users": {
            "total": User.objects.count(),
            "active": User.objects.filter(is_active=True).count(),
            "staff": User.objects.filter(is_staff=True).count(),
        },
        "organizations": {
            "total": Organization.objects.count(),
        },
        "operator_tasks": {
            "open": OperatorTask.objects.filter(status__in=[OperatorTask.Status.OPEN, OperatorTask.Status.IN_PROGRESS, OperatorTask.Status.BLOCKED]).count(),
            "urgent": OperatorTask.objects.filter(priority=OperatorTask.Priority.URGENT).exclude(status__in=[OperatorTask.Status.DONE, OperatorTask.Status.CANCELED]).count(),
            "overdue": OperatorTask.objects.filter(due_at__lt=timezone.now()).exclude(status__in=[OperatorTask.Status.DONE, OperatorTask.Status.CANCELED]).count(),
        },
        "bulk_actions": {
            "pending_approval": BulkActionRequest.objects.filter(status=BulkActionRequest.Status.PENDING_APPROVAL).count(),
            "running": BulkActionRequest.objects.filter(status=BulkActionRequest.Status.RUNNING).count(),
        },
    }

    optional_sources = [
        ("billing_subscriptions", "billing.models", "Subscription", {"status__in": ["active", "trialing"]}),
        ("billing_invoices_open", "billing.models", "Invoice", {"status__in": ["open", "past_due"]}),
        ("security_risk_events_open", "security_ops.models", "RiskEvent", {"status__in": ["open", "acknowledged"]}),
        ("fraud_abuse_cases_open", "fraud_abuse.models", "AbuseCase", {"status__in": ["open", "investigating"]}),
        ("compliance_approvals_pending", "compliance.models", "ApprovalRequest", {"status": "pending"}),
        ("ops_incidents_open", "ops.models", "StatusIncident", {"status__in": ["investigating", "identified", "monitoring"]}),
    ]
    for key, module_name, class_name, filters in optional_sources:
        try:
            module = __import__(module_name, fromlist=[class_name])
            model = getattr(module, class_name)
            data[key] = model.objects.filter(**filters).count()
        except Exception:
            data[key] = None
    return data


def create_dashboard_snapshot(*, user=None, name="global"):
    payload = build_dashboard_summary()
    return DashboardSnapshot.objects.create(
        name=name,
        generated_by=user if getattr(user, "is_authenticated", False) else None,
        payload=payload,
        source_counts={k: v for k, v in payload.items() if isinstance(v, int)},
    )


def task_breakdown_for_user(user):
    qs = OperatorTask.objects.filter(Q(assigned_to=user) | Q(created_by=user)).distinct()
    return {
        "total": qs.count(),
        "open": qs.filter(status=OperatorTask.Status.OPEN).count(),
        "in_progress": qs.filter(status=OperatorTask.Status.IN_PROGRESS).count(),
        "blocked": qs.filter(status=OperatorTask.Status.BLOCKED).count(),
        "done": qs.filter(status=OperatorTask.Status.DONE).count(),
        "by_domain": list(qs.values("domain").annotate(count=Count("id")).order_by("domain")),
    }


def build_admin_console_readiness():
    """Return a production-readiness report for operator/admin workflows."""
    User = get_user_model()
    now = timezone.now()
    checks = []

    def add_check(code, passed, detail, severity="warning"):
        checks.append({
            "code": code,
            "passed": bool(passed),
            "severity": "info" if passed else severity,
            "detail": detail,
        })

    staff_count = User.objects.filter(is_staff=True, is_active=True).count()
    enabled_widgets = DashboardWidget.objects.filter(enabled=True).count()
    open_tasks = OperatorTask.objects.exclude(status__in=[OperatorTask.Status.DONE, OperatorTask.Status.CANCELED]).count()
    pending_bulk = BulkActionRequest.objects.filter(status=BulkActionRequest.Status.PENDING_APPROVAL).count()
    snapshots = DashboardSnapshot.objects.count()

    add_check("staff_operator_exists", staff_count > 0, f"Active staff operators: {staff_count}", "critical")
    add_check("dashboard_widgets_configured", enabled_widgets > 0, f"Enabled dashboard widgets: {enabled_widgets}")
    add_check("operator_task_queue_available", True, f"Open operator tasks: {open_tasks}", "info")
    add_check("bulk_action_approval_workflow", True, f"Pending bulk approvals: {pending_bulk}", "info")
    add_check("dashboard_snapshots_available", snapshots > 0, f"Dashboard snapshots: {snapshots}")

    optional_modules = [
        ("billing", "billing.models", "Subscription"),
        ("security_ops", "security_ops.models", "RiskEvent"),
        ("compliance", "compliance.models", "ApprovalRequest"),
        ("fraud_abuse", "fraud_abuse.models", "AbuseCase"),
        ("ops", "ops.models", "StatusIncident"),
        ("customer_portal", "customer_portal.models", "PortalSupportRequest"),
    ]
    module_status = {}
    for code, module_name, class_name in optional_modules:
        try:
            module = __import__(module_name, fromlist=[class_name])
            getattr(module, class_name)
            module_status[code] = "available"
            add_check(f"module_{code}_available", True, f"{code} admin data source is importable.", "info")
        except Exception as exc:
            module_status[code] = "missing"
            add_check(f"module_{code}_available", False, f"{code} admin data source is not importable: {exc}")

    failing = [c for c in checks if not c["passed"]]
    critical = [c for c in failing if c["severity"] == "critical"]
    return {
        "version": "37.0.0",
        "component": "admin_console",
        "generated_at": now.isoformat(),
        "status": "blocked" if critical else ("needs_attention" if failing else "ready"),
        "summary": {
            "active_staff_operators": staff_count,
            "enabled_widgets": enabled_widgets,
            "open_operator_tasks": open_tasks,
            "pending_bulk_approvals": pending_bulk,
            "dashboard_snapshots": snapshots,
            "optional_modules": module_status,
        },
        "checks": checks,
        "next_acceptance_steps": [
            "Create at least one active staff operator with MFA enabled.",
            "Seed default dashboard widgets for auth, billing, security, support, and ops.",
            "Create a dashboard snapshot after seed data is loaded.",
            "Run an approval drill for one low-risk bulk action before production launch.",
            "Confirm support requests can be escalated into operator tasks.",
        ],
    }
