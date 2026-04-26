from django.utils import timezone

from accounts.audit import write_audit_event
from accounts.models import AuditLog

from .models import AccountRestriction, SecurityRiskEvent


HIGH_RISK_SCORE = 70
CRITICAL_RISK_SCORE = 90


def classify_score(score: int) -> str:
    if score >= CRITICAL_RISK_SCORE:
        return SecurityRiskEvent.Severity.CRITICAL
    if score >= HIGH_RISK_SCORE:
        return SecurityRiskEvent.Severity.HIGH
    if score >= 40:
        return SecurityRiskEvent.Severity.MEDIUM
    return SecurityRiskEvent.Severity.LOW


def create_risk_event(*, category, signal, summary, score=0, user=None, organization=None, subscription=None, request=None, metadata=None):
    event = SecurityRiskEvent.objects.create(
        category=category,
        severity=classify_score(score),
        signal=signal,
        summary=summary,
        score=max(0, min(int(score), 100)),
        user=user,
        organization=organization,
        subscription=subscription,
        ip_address=(request.META.get("REMOTE_ADDR") if request else None),
        user_agent=(request.META.get("HTTP_USER_AGENT", "") if request else ""),
        metadata=metadata or {},
    )
    return event


def has_active_restriction(user, restriction_type, organization=None):
    now = timezone.now()
    queryset = AccountRestriction.objects.filter(
        user=user,
        restriction_type=restriction_type,
        lifted_at__isnull=True,
        starts_at__lte=now,
    ).filter(models_q_expires_active(now))
    if organization is not None:
        queryset = queryset.filter(organization__in=[organization, None])
    return queryset.exists()


def models_q_expires_active(now):
    from django.db.models import Q

    return Q(expires_at__isnull=True) | Q(expires_at__gt=now)


def log_security_admin_action(*, request, action, metadata):
    write_audit_event(
        request=request,
        actor=request.user if request and request.user.is_authenticated else None,
        category=AuditLog.Category.ADMIN,
        action=action,
        metadata=metadata,
    )
