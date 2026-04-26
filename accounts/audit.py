from __future__ import annotations

from typing import Any

from django.utils.encoding import force_str

from .models import AuditLog


def get_client_ip(request) -> str | None:
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "") if request else ""
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR") if request else None


def get_request_id(request) -> str:
    if not request:
        return ""
    return force_str(request.headers.get("X-Request-ID") or request.headers.get("X-Correlation-ID") or "")[:100]


def write_audit_event(
    *,
    request=None,
    actor=None,
    category: str,
    action: str,
    outcome: str = AuditLog.Outcome.SUCCESS,
    client_id: str = "",
    subject_user_id=None,
    metadata: dict[str, Any] | None = None,
) -> AuditLog:
    user_agent = request.META.get("HTTP_USER_AGENT", "")[:2000] if request else ""
    return AuditLog.objects.create(
        actor=actor if getattr(actor, "is_authenticated", False) and getattr(actor, "_meta", None) is not None else None,
        category=category,
        action=action,
        outcome=outcome,
        ip_address=get_client_ip(request),
        user_agent=user_agent,
        request_id=get_request_id(request),
        client_id=client_id[:120] if client_id else "",
        subject_user_id=subject_user_id,
        metadata=metadata or {},
    )
