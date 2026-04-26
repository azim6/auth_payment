from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from security_ops.models import AccountRestriction, SecurityRiskEvent

from .models import AbuseCase, AbuseSignal, DeviceFingerprint, IPReputation, PaymentRiskReview, VelocityEvent, VelocityRule


def score_to_severity(score: int) -> str:
    if score >= 90:
        return AbuseSignal.Severity.CRITICAL
    if score >= 70:
        return AbuseSignal.Severity.HIGH
    if score >= 40:
        return AbuseSignal.Severity.MEDIUM
    if score >= 10:
        return AbuseSignal.Severity.LOW
    return AbuseSignal.Severity.INFO


def register_abuse_signal(*, category, signal, score, summary, user=None, organization=None, subscription=None, device=None, ip_reputation=None, ip_address=None, user_agent="", metadata=None, idempotency_key=None):
    defaults = {
        "category": category,
        "signal": signal,
        "score": score,
        "severity": score_to_severity(score),
        "summary": summary,
        "user": user,
        "organization": organization,
        "subscription": subscription,
        "device": device,
        "ip_reputation": ip_reputation,
        "ip_address": ip_address,
        "user_agent": user_agent,
        "metadata": metadata or {},
    }
    if idempotency_key:
        obj, _ = AbuseSignal.objects.get_or_create(event_idempotency_key=idempotency_key, defaults=defaults)
        return obj
    return AbuseSignal.objects.create(**defaults)


def record_velocity_event(*, event_name, user=None, organization=None, device=None, ip_address=None, metadata=None, occurred_at=None):
    return VelocityEvent.objects.create(
        event_name=event_name,
        user=user,
        organization=organization,
        device=device,
        ip_address=ip_address,
        metadata=metadata or {},
        occurred_at=occurred_at or timezone.now(),
    )


def _scope_filter(rule, event):
    if rule.scope == "user" and event.user_id:
        return Q(user_id=event.user_id)
    if rule.scope == "organization" and event.organization_id:
        return Q(organization_id=event.organization_id)
    if rule.scope == "ip" and event.ip_address:
        return Q(ip_address=event.ip_address)
    if rule.scope == "device" and event.device_id:
        return Q(device_id=event.device_id)
    if rule.scope == "global":
        return Q()
    return None


def evaluate_velocity_rules(event):
    matches = []
    rules = VelocityRule.objects.filter(enabled=True, event_name=event.event_name)
    now = timezone.now()
    for rule in rules:
        scope_q = _scope_filter(rule, event)
        if scope_q is None:
            continue
        since = now - timedelta(seconds=rule.window_seconds)
        count = VelocityEvent.objects.filter(event_name=rule.event_name, occurred_at__gte=since).filter(scope_q).count()
        if count >= rule.threshold:
            abuse_signal = register_abuse_signal(
                category=AbuseSignal.Category.API,
                signal=f"velocity.{rule.event_name}.{rule.scope}",
                score=rule.risk_score,
                summary=f"Velocity rule matched: {rule.name}",
                user=event.user,
                organization=event.organization,
                device=event.device,
                ip_address=event.ip_address,
                metadata={"rule_id": str(rule.id), "count": count, "window_seconds": rule.window_seconds, "action": rule.action},
                idempotency_key=f"velocity:{rule.id}:{event.id}",
            )
            matches.append({"rule": rule, "count": count, "signal": abuse_signal})
    return matches


def create_security_risk_from_abuse_signal(abuse_signal):
    severity_map = {
        AbuseSignal.Severity.INFO: SecurityRiskEvent.Severity.LOW,
        AbuseSignal.Severity.LOW: SecurityRiskEvent.Severity.LOW,
        AbuseSignal.Severity.MEDIUM: SecurityRiskEvent.Severity.MEDIUM,
        AbuseSignal.Severity.HIGH: SecurityRiskEvent.Severity.HIGH,
        AbuseSignal.Severity.CRITICAL: SecurityRiskEvent.Severity.CRITICAL,
    }
    category_map = {
        AbuseSignal.Category.AUTH: SecurityRiskEvent.Category.AUTH,
        AbuseSignal.Category.BILLING: SecurityRiskEvent.Category.BILLING,
        AbuseSignal.Category.PAYMENT: SecurityRiskEvent.Category.BILLING,
        AbuseSignal.Category.API: SecurityRiskEvent.Category.PLATFORM,
        AbuseSignal.Category.CONTENT: SecurityRiskEvent.Category.PLATFORM,
        AbuseSignal.Category.NOTIFICATION: SecurityRiskEvent.Category.PLATFORM,
        AbuseSignal.Category.PLATFORM: SecurityRiskEvent.Category.PLATFORM,
    }
    return SecurityRiskEvent.objects.create(
        category=category_map.get(abuse_signal.category, SecurityRiskEvent.Category.PLATFORM),
        severity=severity_map.get(abuse_signal.severity, SecurityRiskEvent.Severity.LOW),
        signal=f"fraud_abuse.{abuse_signal.signal}",
        score=abuse_signal.score,
        user=abuse_signal.user,
        organization=abuse_signal.organization,
        subscription=abuse_signal.subscription,
        ip_address=abuse_signal.ip_address,
        user_agent=abuse_signal.user_agent,
        summary=abuse_signal.summary,
        metadata={"abuse_signal_id": str(abuse_signal.id), **(abuse_signal.metadata or {})},
    )


def apply_safe_enforcement(*, user, organization=None, restriction_type=AccountRestriction.RestrictionType.API_BLOCK, reason, actor=None, expires_at=None, metadata=None):
    return AccountRestriction.objects.create(
        user=user,
        organization=organization,
        restriction_type=restriction_type,
        reason=reason,
        expires_at=expires_at,
        created_by=actor,
        metadata=metadata or {},
    )


def summarize_subject_risk(*, user=None, organization=None, ip_address=None):
    open_cases = AbuseCase.objects.all()
    payment_reviews = PaymentRiskReview.objects.all()
    signals = AbuseSignal.objects.all()
    restrictions = AccountRestriction.objects.filter(lifted_at__isnull=True)
    if user:
        open_cases = open_cases.filter(user=user)
        signals = signals.filter(user=user)
        restrictions = restrictions.filter(user=user)
    if organization:
        open_cases = open_cases.filter(organization=organization)
        payment_reviews = payment_reviews.filter(organization=organization)
        signals = signals.filter(organization=organization)
        restrictions = restrictions.filter(Q(organization=organization) | Q(organization__isnull=True))
    if ip_address:
        signals = signals.filter(ip_address=ip_address)
    recent_signals = signals.order_by("-observed_at")[:25]
    max_score = max([s.score for s in recent_signals], default=0)
    return {
        "max_recent_score": max_score,
        "recent_signal_count": signals.count(),
        "open_case_count": open_cases.exclude(status__in=[AbuseCase.Status.RESOLVED, AbuseCase.Status.FALSE_POSITIVE]).count(),
        "pending_payment_review_count": payment_reviews.filter(status=PaymentRiskReview.Status.PENDING).count(),
        "active_restriction_count": sum(1 for restriction in restrictions[:100] if restriction.is_active),
        "recent_signals": recent_signals,
    }


def upsert_device_fingerprint(*, fingerprint_hash, user=None, organization=None, metadata=None):
    obj, created = DeviceFingerprint.objects.get_or_create(
        fingerprint_hash=fingerprint_hash,
        defaults={"last_user": user, "last_organization": organization, "metadata": metadata or {}},
    )
    obj.last_seen_at = timezone.now()
    obj.last_user = user or obj.last_user
    obj.last_organization = organization or obj.last_organization
    if metadata:
        merged = obj.metadata or {}
        merged.update(metadata)
        obj.metadata = merged
    obj.save(update_fields=["last_seen_at", "last_user", "last_organization", "metadata", "updated_at"])
    return obj


def upsert_ip_reputation(*, ip_address, reputation=IPReputation.Reputation.UNKNOWN, risk_score=0, source="internal", metadata=None):
    obj, _ = IPReputation.objects.get_or_create(ip_address=ip_address, defaults={"reputation": reputation, "risk_score": risk_score, "source": source, "metadata": metadata or {}})
    obj.last_seen_at = timezone.now()
    obj.risk_score = max(obj.risk_score, risk_score)
    if reputation != IPReputation.Reputation.UNKNOWN:
        obj.reputation = reputation
    if metadata:
        merged = obj.metadata or {}
        merged.update(metadata)
        obj.metadata = merged
    obj.save(update_fields=["last_seen_at", "risk_score", "reputation", "metadata", "updated_at"])
    return obj
