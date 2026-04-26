from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any

from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.utils import timezone

from .models import EnvironmentCheck, ServiceHealthCheck, BackupSnapshot, ReleaseRecord


@dataclass(frozen=True)
class CheckResult:
    key: str
    status: str
    message: str
    details: dict[str, Any]


def evaluate_environment() -> list[CheckResult]:
    """Return deploy-safety checks that are safe to expose only to staff."""
    results: list[CheckResult] = []
    results.append(CheckResult(
        key="debug_disabled",
        status=EnvironmentCheck.Status.PASS if not settings.DEBUG else EnvironmentCheck.Status.FAIL,
        message="DEBUG must be false in production.",
        details={"debug": settings.DEBUG},
    ))
    results.append(CheckResult(
        key="secret_key_not_default",
        status=EnvironmentCheck.Status.PASS if settings.SECRET_KEY != "unsafe-dev-secret-change-me" and len(settings.SECRET_KEY) >= 40 else EnvironmentCheck.Status.FAIL,
        message="SECRET_KEY must be long, random, and environment-provided.",
        details={"length": len(settings.SECRET_KEY)},
    ))
    results.append(CheckResult(
        key="allowed_hosts_configured",
        status=EnvironmentCheck.Status.PASS if settings.ALLOWED_HOSTS and "*" not in settings.ALLOWED_HOSTS else EnvironmentCheck.Status.FAIL,
        message="ALLOWED_HOSTS must not be wildcard in production.",
        details={"allowed_hosts": settings.ALLOWED_HOSTS},
    ))
    results.append(CheckResult(
        key="secure_cookies",
        status=EnvironmentCheck.Status.PASS if settings.SESSION_COOKIE_HTTPONLY and settings.SESSION_COOKIE_SECURE else EnvironmentCheck.Status.WARN,
        message="Session cookies should be HttpOnly and Secure.",
        details={"SESSION_COOKIE_HTTPONLY": settings.SESSION_COOKIE_HTTPONLY, "SESSION_COOKIE_SECURE": settings.SESSION_COOKIE_SECURE},
    ))
    results.append(CheckResult(
        key="csrf_trusted_origins",
        status=EnvironmentCheck.Status.PASS if getattr(settings, "CSRF_TRUSTED_ORIGINS", []) else EnvironmentCheck.Status.WARN,
        message="CSRF_TRUSTED_ORIGINS should list trusted web frontends.",
        details={"count": len(getattr(settings, "CSRF_TRUSTED_ORIGINS", []))},
    ))
    return results


def persist_environment_checks() -> list[EnvironmentCheck]:
    records: list[EnvironmentCheck] = []
    for result in evaluate_environment():
        record, _ = EnvironmentCheck.objects.update_or_create(
            key=result.key,
            defaults={
                "status": result.status,
                "message": result.message,
                "details": result.details,
                "checked_at": timezone.now(),
            },
        )
        records.append(record)
    return records


def run_health_checks() -> list[ServiceHealthCheck]:
    checks: list[tuple[str, str, str, int, dict[str, Any]]] = []

    start = time.perf_counter()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        checks.append(("database", ServiceHealthCheck.Status.HEALTHY, "Database responded.", int((time.perf_counter() - start) * 1000), {}))
    except Exception as exc:  # pragma: no cover - runtime diagnostic path
        checks.append(("database", ServiceHealthCheck.Status.DOWN, str(exc), int((time.perf_counter() - start) * 1000), {}))

    start = time.perf_counter()
    try:
        cache.set("ops:healthcheck", "ok", timeout=15)
        ok = cache.get("ops:healthcheck") == "ok"
        checks.append(("cache", ServiceHealthCheck.Status.HEALTHY if ok else ServiceHealthCheck.Status.DEGRADED, "Cache round-trip completed." if ok else "Cache write/read mismatch.", int((time.perf_counter() - start) * 1000), {}))
    except Exception as exc:  # pragma: no cover - runtime diagnostic path
        checks.append(("cache", ServiceHealthCheck.Status.DOWN, str(exc), int((time.perf_counter() - start) * 1000), {}))

    records: list[ServiceHealthCheck] = []
    for name, status, message, latency_ms, metadata in checks:
        record, _ = ServiceHealthCheck.objects.update_or_create(
            name=name,
            defaults={"status": status, "message": message, "latency_ms": latency_ms, "metadata": metadata, "checked_at": timezone.now()},
        )
        records.append(record)
    return records


def build_readiness_payload() -> dict[str, Any]:
    health = run_health_checks()
    env_checks = persist_environment_checks()
    healthy = all(check.status == ServiceHealthCheck.Status.HEALTHY for check in health)
    safe = all(check.status != EnvironmentCheck.Status.FAIL for check in env_checks)
    return {
        "ready": healthy and safe,
        "health": {check.name: check.status for check in health},
        "environment": {check.key: check.status for check in env_checks},
        "version": getattr(settings, "APP_VERSION", "unknown"),
    }


def mark_backup_running(snapshot: BackupSnapshot) -> BackupSnapshot:
    snapshot.status = BackupSnapshot.Status.RUNNING
    snapshot.started_at = timezone.now()
    snapshot.save(update_fields=["status", "started_at"])
    return snapshot


def mark_release_deployed(release: ReleaseRecord, actor=None) -> ReleaseRecord:
    release.status = ReleaseRecord.Status.RELEASED
    release.deployed_at = timezone.now()
    if actor and getattr(actor, "is_authenticated", False):
        release.deployed_by = actor
    release.save(update_fields=["status", "deployed_at", "deployed_by"])
    return release


def _status_from_bool(ok: bool, strict: bool = True) -> str:
    if ok:
        return "pass"
    return "fail" if strict else "warn"


def build_production_boot_validation_payload() -> dict[str, Any]:
    """Build an operator-friendly production boot validation report.

    This report is intentionally conservative and read-only. It is designed for
    CI/CD release gates, Docker Compose smoke checks, and the separate Admin
    Control Platform readiness screen.
    """
    checks: list[dict[str, Any]] = []

    def add(key: str, ok: bool, message: str, details: dict[str, Any] | None = None, strict: bool = True) -> None:
        checks.append({
            "key": key,
            "status": _status_from_bool(ok, strict=strict),
            "message": message,
            "details": details or {},
            "strict": strict,
        })

    add("debug_disabled", not settings.DEBUG, "DEBUG must be false outside local development.", {"debug": settings.DEBUG})
    add("secret_key_safe", settings.SECRET_KEY != "unsafe-dev-secret-change-me" and len(settings.SECRET_KEY) >= 40, "SECRET_KEY must be long and environment-provided.", {"length": len(settings.SECRET_KEY)})
    add("allowed_hosts_safe", bool(settings.ALLOWED_HOSTS) and "*" not in settings.ALLOWED_HOSTS, "ALLOWED_HOSTS must be explicit.", {"allowed_hosts": settings.ALLOWED_HOSTS})
    add("secure_cookie_flags", bool(settings.SESSION_COOKIE_HTTPONLY and settings.SESSION_COOKIE_SECURE and settings.CSRF_COOKIE_SECURE), "Session/CSRF cookies must use secure production flags.", {
        "SESSION_COOKIE_HTTPONLY": settings.SESSION_COOKIE_HTTPONLY,
        "SESSION_COOKIE_SECURE": settings.SESSION_COOKIE_SECURE,
        "CSRF_COOKIE_SECURE": settings.CSRF_COOKIE_SECURE,
    })
    add("csrf_origins_configured", bool(getattr(settings, "CSRF_TRUSTED_ORIGINS", [])), "CSRF_TRUSTED_ORIGINS should include trusted web/admin frontends.", {"origins": getattr(settings, "CSRF_TRUSTED_ORIGINS", [])})
    add("cors_origins_configured", bool(getattr(settings, "CORS_ALLOWED_ORIGINS", [])), "CORS_ALLOWED_ORIGINS should be explicit for browser clients.", {"origins": getattr(settings, "CORS_ALLOWED_ORIGINS", [])})

    expected_hosts = getattr(settings, "PRODUCTION_BOOT_EXPECTED_HOSTS", [])
    if expected_hosts:
        add("expected_hosts_present", all(host in settings.ALLOWED_HOSTS for host in expected_hosts), "Expected production hosts must be present in ALLOWED_HOSTS.", {"expected": expected_hosts, "actual": settings.ALLOWED_HOSTS})

    expected_origins = getattr(settings, "PRODUCTION_BOOT_EXPECTED_ORIGINS", [])
    if expected_origins:
        configured = set(getattr(settings, "CSRF_TRUSTED_ORIGINS", [])) | set(getattr(settings, "CORS_ALLOWED_ORIGINS", []))
        add("expected_admin_origins_present", all(origin in configured for origin in expected_origins), "Admin frontend/API origins should be trusted explicitly.", {"expected": expected_origins, "configured": sorted(configured)})

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        add("database_connectivity", True, "Database connection succeeded.")
    except Exception as exc:  # pragma: no cover - deployment diagnostic
        add("database_connectivity", False, "Database connection failed.", {"error": str(exc)})

    try:
        cache.set("ops:production_boot_validation", "ok", timeout=15)
        add("cache_connectivity", cache.get("ops:production_boot_validation") == "ok", "Cache round-trip should succeed.")
    except Exception as exc:  # pragma: no cover - deployment diagnostic
        add("cache_connectivity", False, "Cache connection failed.", {"error": str(exc)})

    strict_optionals = getattr(settings, "PRODUCTION_BOOT_STRICT_OPTIONALS", False)
    add("stripe_configured", bool(getattr(settings, "STRIPE_SECRET_KEY", "") and getattr(settings, "STRIPE_WEBHOOK_SECRET", "")), "Stripe secret key and webhook secret should be configured before accepting payments.", strict=strict_optionals)
    add("email_configured", bool(getattr(settings, "EMAIL_HOST", "") and getattr(settings, "DEFAULT_FROM_EMAIL", "")), "SMTP email delivery should be configured before launch.", strict=strict_optionals)
    add("backup_storage_configured", bool(getattr(settings, "BACKUP_STORAGE_BASE_URI", "")), "Backup storage URI should be configured before production launch.", strict=strict_optionals)

    failed = [check for check in checks if check["status"] == "fail"]
    warned = [check for check in checks if check["status"] == "warn"]
    return {
        "ready": not failed,
        "summary": {"pass": sum(1 for c in checks if c["status"] == "pass"), "warn": len(warned), "fail": len(failed)},
        "checks": checks,
        "version": getattr(settings, "APP_VERSION", "unknown"),
        "checked_at": timezone.now().isoformat(),
        "admin_system_compatible": not failed,
        "admin_system_notes": [
            "The separate Admin Control Platform should call /api/v1/admin-integration/readiness/ and this endpoint before release.",
            "Production admin API traffic should be signed, allowlisted, MFA-gated, and audited.",
        ],
    }
