import secrets

from django.contrib.auth.hashers import check_password, make_password
from django.utils import timezone

from .models import PortalActivityLog, PortalApiKey

PORTAL_API_KEY_SCOPES = {
    "profile:read",
    "profile:write",
    "org:read",
    "org:write",
    "billing:read",
    "billing:write",
    "privacy:read",
    "privacy:write",
    "support:write",
}


def validate_portal_scopes(scope_string: str) -> str:
    requested = {scope for scope in scope_string.split() if scope}
    unknown = requested - PORTAL_API_KEY_SCOPES
    if unknown:
        raise ValueError(f"Unsupported portal API scopes: {', '.join(sorted(unknown))}")
    return " ".join(sorted(requested))


def generate_portal_api_key() -> str:
    return f"cpak_{secrets.token_urlsafe(40)}"


def portal_api_key_prefix(raw_key: str) -> str:
    return raw_key[:18]


def create_portal_api_key(*, user, organization=None, name: str, scopes: str = "", expires_at=None, allowed_origins=None, allowed_ips=None):
    raw_key = generate_portal_api_key()
    key = PortalApiKey.objects.create(
        user=user,
        organization=organization,
        name=name,
        key_prefix=portal_api_key_prefix(raw_key),
        key_hash=make_password(raw_key),
        scopes=validate_portal_scopes(scopes),
        expires_at=expires_at,
        allowed_origins=allowed_origins or [],
        allowed_ips=allowed_ips or [],
    )
    record_portal_activity(
        user=user,
        organization=organization,
        domain=PortalActivityLog.Domain.API,
        event_type="portal_api_key.created",
        title="API key created",
        summary=f"Customer portal API key '{name}' was created.",
    )
    return key, raw_key


def find_valid_portal_api_key(raw_key: str) -> PortalApiKey | None:
    if not raw_key or not raw_key.startswith("cpak_"):
        return None
    key = PortalApiKey.objects.select_related("user", "organization").filter(
        key_prefix=portal_api_key_prefix(raw_key),
        status=PortalApiKey.Status.ACTIVE,
    ).first()
    if not key or not key.is_active:
        return None
    if not check_password(raw_key, key.key_hash):
        return None
    key.mark_used()
    return key


def record_portal_activity(*, user, domain, event_type, title, organization=None, summary="", request=None, metadata=None):
    ip = None
    user_agent = ""
    if request is not None:
        ip = request.META.get("HTTP_X_FORWARDED_FOR", request.META.get("REMOTE_ADDR", "")).split(",")[0] or None
        user_agent = request.META.get("HTTP_USER_AGENT", "")[:2000]
    return PortalActivityLog.objects.create(
        user=user,
        organization=organization,
        domain=domain,
        event_type=event_type,
        title=title,
        summary=summary,
        ip_address=ip,
        user_agent=user_agent,
        metadata=metadata or {},
    )


def build_portal_summary(user):
    from accounts.models import OrganizationMembership
    from billing.models import BillingCustomer, Subscription, Invoice
    from customer_portal.models import PortalSupportRequest

    memberships = OrganizationMembership.objects.filter(user=user).select_related("organization")
    org_ids = [m.organization_id for m in memberships]
    customers = BillingCustomer.objects.filter(organization_id__in=org_ids)
    customer_ids = list(customers.values_list("id", flat=True))
    active_subscriptions = Subscription.objects.filter(customer_id__in=customer_ids, status__in=["active", "trialing", "free"]).count()
    open_support_requests = PortalSupportRequest.objects.filter(user=user).exclude(status__in=["resolved", "closed"]).count()
    unpaid_invoices = Invoice.objects.filter(customer_id__in=customer_ids, status__in=["open", "past_due"]).count()
    return {
        "user_id": str(user.id),
        "email": user.email,
        "organizations": memberships.count(),
        "active_subscriptions": active_subscriptions,
        "unpaid_invoices": unpaid_invoices,
        "open_support_requests": open_support_requests,
        "generated_at": timezone.now().isoformat(),
    }


def build_customer_portal_readiness():
    """Return a production-readiness report for customer self-service workflows."""
    from accounts.models import OrganizationMembership
    from billing.models import BillingCustomer, Invoice, Subscription
    from customer_portal.models import PortalOrganizationBookmark, PortalProfileSettings, PortalSupportRequest

    now = timezone.now()
    checks = []

    def add_check(code, passed, detail, severity="warning"):
        checks.append({
            "code": code,
            "passed": bool(passed),
            "severity": "info" if passed else severity,
            "detail": detail,
        })

    profile_settings = PortalProfileSettings.objects.count()
    memberships = OrganizationMembership.objects.count()
    billing_customers = BillingCustomer.objects.count()
    subscriptions = Subscription.objects.count()
    invoices = Invoice.objects.count()
    open_support = PortalSupportRequest.objects.exclude(status__in=[PortalSupportRequest.Status.RESOLVED, PortalSupportRequest.Status.CLOSED]).count()
    active_api_keys = PortalApiKey.objects.filter(status=PortalApiKey.Status.ACTIVE).count()
    activity_logs = PortalActivityLog.objects.count()
    bookmarks = PortalOrganizationBookmark.objects.count()

    add_check("profile_settings_available", True, f"Portal profile rows: {profile_settings}", "info")
    add_check("organization_memberships_visible", memberships > 0, f"Organization memberships: {memberships}")
    add_check("billing_summary_source_available", billing_customers > 0 or subscriptions > 0 or invoices > 0, f"Billing customers/subscriptions/invoices: {billing_customers}/{subscriptions}/{invoices}")
    add_check("support_request_queue_available", True, f"Open customer support requests: {open_support}", "info")
    add_check("portal_api_key_controls_available", True, f"Active customer portal API keys: {active_api_keys}", "info")
    add_check("customer_activity_log_available", activity_logs > 0, f"Customer-visible activity events: {activity_logs}")
    add_check("bookmarks_available", True, f"Organization bookmarks: {bookmarks}", "info")

    failing = [c for c in checks if not c["passed"]]
    return {
        "version": "37.0.0",
        "component": "customer_portal",
        "generated_at": now.isoformat(),
        "status": "needs_attention" if failing else "ready",
        "summary": {
            "profile_settings": profile_settings,
            "organization_memberships": memberships,
            "billing_customers": billing_customers,
            "subscriptions": subscriptions,
            "invoices": invoices,
            "open_support_requests": open_support,
            "active_portal_api_keys": active_api_keys,
            "activity_logs": activity_logs,
            "bookmarks": bookmarks,
        },
        "checks": checks,
        "next_acceptance_steps": [
            "Confirm each customer can view only organizations where they are a member.",
            "Confirm billing summary hides raw provider/payment data.",
            "Create, use, and revoke a portal API key in staging.",
            "Create a support request and escalate it to an admin-console operator task.",
            "Confirm activity log entries never expose secrets, tokens, or payment card data.",
        ],
    }


def escalate_support_request_to_operator_task(*, support_request, operator=None):
    """Create an admin-console task from a customer support request."""
    from admin_console.models import OperatorTask

    if support_request.operator_task_id:
        return OperatorTask.objects.filter(id=support_request.operator_task_id).first()

    task = OperatorTask.objects.create(
        title=f"Support: {support_request.subject}",
        domain=OperatorTask.Domain.BILLING if support_request.category == support_request.Category.BILLING else OperatorTask.Domain.SUPPORT,
        priority=support_request.priority if support_request.priority in dict(OperatorTask.Priority.choices) else OperatorTask.Priority.NORMAL,
        description=support_request.message,
        target_type="customer_portal.PortalSupportRequest",
        target_id=str(support_request.id),
        organization=support_request.organization,
        created_by=operator if getattr(operator, "is_authenticated", False) else None,
        metadata={
            "customer_user_id": str(support_request.user_id),
            "category": support_request.category,
            "related_object_type": support_request.related_object_type,
            "related_object_id": support_request.related_object_id,
        },
    )
    support_request.operator_task_id = task.id
    support_request.status = support_request.Status.WAITING_ON_SUPPORT
    support_request.save(update_fields=["operator_task_id", "status", "updated_at"])
    record_portal_activity(
        user=support_request.user,
        organization=support_request.organization,
        domain=PortalActivityLog.Domain.ORGANIZATION if support_request.organization else PortalActivityLog.Domain.AUTH,
        event_type="support_request.escalated",
        title="Support request escalated",
        summary=support_request.subject,
        metadata={"operator_task_id": str(task.id)},
    )
    return task
