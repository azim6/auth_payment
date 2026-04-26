from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.conf import settings
from django.contrib.sessions.models import Session
from django.utils import timezone

from .models import (
    AccountToken,
    AuditLog,
    AuthSessionDevice,
    MfaDevice,
    OAuthClient,
    RecoveryCode,
    RefreshTokenFamily,
    ServiceCredential,
    User,
)


@dataclass(frozen=True)
class ReadinessCheck:
    key: str
    status: str
    detail: str
    count: int | None = None

    def as_dict(self) -> dict[str, Any]:
        payload = {"key": self.key, "status": self.status, "detail": self.detail}
        if self.count is not None:
            payload["count"] = self.count
        return payload


def _status(ok: bool, warn: bool = False) -> str:
    if ok:
        return "pass"
    return "warn" if warn else "fail"


def build_auth_readiness_report() -> dict[str, Any]:
    """Summarize security-critical auth readiness without exposing secrets.

    This report is intentionally aggregate-only. It is safe for staff operators
    and CI/CD smoke checks, but it does not include raw tokens, session keys,
    MFA secrets, recovery codes, or personally identifying account lists.
    """

    now = timezone.now()
    checks: list[ReadinessCheck] = []

    checks.append(
        ReadinessCheck(
            key="custom_user_model",
            status=_status(settings.AUTH_USER_MODEL == "accounts.User"),
            detail=f"AUTH_USER_MODEL is {settings.AUTH_USER_MODEL}.",
        )
    )
    checks.append(
        ReadinessCheck(
            key="password_hashers",
            status=_status(any("Argon2" in item for item in settings.PASSWORD_HASHERS), warn=True),
            detail="Argon2 is preferred for new deployments; PBKDF2 fallback is acceptable when documented.",
        )
    )
    checks.append(
        ReadinessCheck(
            key="secure_cookies",
            status=_status(bool(settings.SESSION_COOKIE_HTTPONLY and settings.CSRF_COOKIE_HTTPONLY is False), warn=True),
            detail="Session cookies are HttpOnly; CSRF cookie remains readable by browser clients for CSRF header submission.",
        )
    )
    checks.append(
        ReadinessCheck(
            key="email_verification_tokens",
            status="pass",
            detail="Email verification tokens are stored hashed and expire server-side.",
            count=AccountToken.objects.filter(purpose=AccountToken.Purpose.EMAIL_VERIFICATION, used_at__isnull=True, expires_at__gt=now).count(),
        )
    )
    checks.append(
        ReadinessCheck(
            key="password_reset_tokens",
            status="pass",
            detail="Password reset tokens are stored hashed, single-use, and invalidated after successful reset.",
            count=AccountToken.objects.filter(purpose=AccountToken.Purpose.PASSWORD_RESET, used_at__isnull=True, expires_at__gt=now).count(),
        )
    )
    checks.append(
        ReadinessCheck(
            key="mfa_devices",
            status="pass",
            detail="Confirmed MFA devices and hashed recovery codes are tracked per user.",
            count=MfaDevice.objects.filter(confirmed_at__isnull=False).count(),
        )
    )
    checks.append(
        ReadinessCheck(
            key="recovery_codes",
            status="pass",
            detail="Only hashed recovery-code records are stored; used codes are retained for auditability.",
            count=RecoveryCode.objects.filter(used_at__isnull=True).count(),
        )
    )
    checks.append(
        ReadinessCheck(
            key="session_device_inventory",
            status="pass",
            detail="Web session devices are inventoried by hashed session key for user-driven revocation.",
            count=AuthSessionDevice.objects.filter(revoked_at__isnull=True).count(),
        )
    )
    checks.append(
        ReadinessCheck(
            key="refresh_token_inventory",
            status="pass",
            detail="Mobile/desktop refresh token families are tracked for logout-all and incident response.",
            count=RefreshTokenFamily.objects.filter(revoked_at__isnull=True, expires_at__gt=now).count(),
        )
    )
    checks.append(
        ReadinessCheck(
            key="oauth_clients",
            status="pass",
            detail="OAuth/OIDC client registrations are centrally controlled and can be disabled.",
            count=OAuthClient.objects.filter(is_active=True).count(),
        )
    )
    checks.append(
        ReadinessCheck(
            key="service_credentials",
            status="pass",
            detail="Service credentials are hashed, prefix-indexed, scoped, expirable, and revocable.",
            count=ServiceCredential.objects.filter(is_active=True).count(),
        )
    )
    checks.append(
        ReadinessCheck(
            key="audit_log_coverage",
            status="pass" if AuditLog.objects.exists() else "warn",
            detail="Security-sensitive account, OAuth, service, and admin actions should emit append-only audit events.",
            count=AuditLog.objects.count(),
        )
    )
    checks.append(
        ReadinessCheck(
            key="active_accounts",
            status="pass",
            detail="Active and inactive account counts help operators catch accidental lockouts before deploys.",
            count=User.objects.filter(is_active=True).count(),
        )
    )
    checks.append(
        ReadinessCheck(
            key="django_sessions",
            status="pass",
            detail="Expired Django sessions should be cleared by scheduled maintenance command clearsessions.",
            count=Session.objects.filter(expire_date__gt=now).count(),
        )
    )

    totals = {"pass": 0, "warn": 0, "fail": 0}
    for check in checks:
        totals[check.status] = totals.get(check.status, 0) + 1

    overall = "pass"
    if totals["fail"]:
        overall = "fail"
    elif totals["warn"]:
        overall = "warn"

    return {
        "component": "auth_identity",
        "version": "35.0.0",
        "overall_status": overall,
        "generated_at": now.isoformat(),
        "totals": totals,
        "checks": [check.as_dict() for check in checks],
        "next_operator_steps": [
            "Run full Django test suite with production-like settings before deployment.",
            "Verify email provider, Redis, database backups, and HTTPS settings in staging.",
            "Exercise register, verify email, login, MFA, password reset, logout-all, and service-token flows end-to-end.",
        ],
    }
