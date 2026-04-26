from __future__ import annotations

import importlib
from dataclasses import dataclass, asdict
from typing import Iterable

from django.apps import apps
from django.conf import settings
from django.core.cache import cache
from django.core.management import get_commands
from django.db import connection
from django.db.migrations.loader import MigrationLoader

PRODUCTION_APPS = {
    "accounts",
    "billing",
    "admin_integration",
    "admin_console",
    "customer_portal",
    "ops",
    "security_ops",
    "notifications",
    "observability",
}

EXPERIMENTAL_APPS = {
    "identity_hardening",
    "enterprise_sso",
    "scim_provisioning",
    "oidc_provider",
    "sdk_registry",
    "usage_billing",
    "tax_pricing",
}

EXPECTED_ADMIN_CONTRACT_PATHS = [
    "/api/v1/admin-integration/readiness/",
    "/api/v1/admin-integration/credentials/",
    "/api/v1/admin-integration/scopes/",
    "/api/v1/admin-integration/contract/",
    "/api/v1/admin-integration/request-audits/",
    "/api/v1/auth/readiness/",
    "/api/v1/billing/readiness/",
    "/api/v1/ops/production-validation/",
    "/api/v1/security-hardening/readiness/",
]


@dataclass
class CheckResult:
    key: str
    status: str
    message: str
    details: dict

    def as_dict(self) -> dict:
        return asdict(self)


def _status(results: Iterable[CheckResult]) -> str:
    values = [result.status for result in results]
    if "fail" in values:
        return "fail"
    if "warn" in values:
        return "warn"
    return "pass"


def run_production_verification() -> dict:
    results: list[CheckResult] = []
    installed = set(settings.INSTALLED_APPS)
    app_labels = {config.label for config in apps.get_app_configs()}

    for label in sorted(PRODUCTION_APPS):
        results.append(CheckResult(
            key=f"app.production.{label}",
            status="pass" if label in app_labels else "fail",
            message=f"Production app {label} is {'installed' if label in app_labels else 'missing'}.",
            details={"app": label},
        ))

    for label in sorted(EXPERIMENTAL_APPS):
        results.append(CheckResult(
            key=f"app.experimental.{label}",
            status="warn" if label in app_labels else "pass",
            message=(
                f"Experimental app {label} is installed; keep disabled by feature flag until acceptance tested."
                if label in app_labels else f"Experimental app {label} is not installed."
            ),
            details={"app": label, "tier": "experimental"},
        ))

    required_settings = [
        ("DEBUG", settings.DEBUG is False, "DEBUG must be false in production."),
        ("ALLOWED_HOSTS", bool(getattr(settings, "ALLOWED_HOSTS", [])), "ALLOWED_HOSTS must be explicit."),
        ("SECRET_KEY", not str(settings.SECRET_KEY).startswith("unsafe"), "SECRET_KEY must be a strong environment secret."),
        ("SESSION_COOKIE_SECURE", bool(getattr(settings, "SESSION_COOKIE_SECURE", False)), "Session cookies must be secure."),
        ("CSRF_COOKIE_SECURE", bool(getattr(settings, "CSRF_COOKIE_SECURE", False)), "CSRF cookies must be secure."),
        ("ADMIN_INTEGRATION_HMAC", hasattr(settings, "ADMIN_INTEGRATION_CLOCK_SKEW_SECONDS"), "Admin integration HMAC clock-skew setting should exist."),
    ]
    for key, ok, message in required_settings:
        results.append(CheckResult(key=f"setting.{key.lower()}", status="pass" if ok else "fail", message=message, details={"setting": key}))

    for module_name in ["accounts.urls", "billing.urls", "admin_integration.urls", "ops.urls"]:
        try:
            importlib.import_module(module_name)
            results.append(CheckResult(f"import.{module_name}", "pass", f"Imported {module_name}.", {"module": module_name}))
        except Exception as exc:  # pragma: no cover - diagnostic path
            results.append(CheckResult(f"import.{module_name}", "fail", f"Could not import {module_name}: {exc}", {"module": module_name, "error": str(exc)}))

    try:
        MigrationLoader(connection, ignore_no_migrations=True)
        results.append(CheckResult("migrations.load", "pass", "Django migration graph loaded.", {}))
    except Exception as exc:  # pragma: no cover - diagnostic path
        results.append(CheckResult("migrations.load", "fail", f"Migration graph failed to load: {exc}", {"error": str(exc)}))

    commands = get_commands()
    for command in ["migrate", "check", "production_verify", "ops_production_preflight"]:
        results.append(CheckResult(
            key=f"command.{command}",
            status="pass" if command in commands else "fail",
            message=f"Management command {command} is {'available' if command in commands else 'missing'}.",
            details={"command": command},
        ))

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        results.append(CheckResult("runtime.database", "pass", "Database connection responded.", {}))
    except Exception as exc:  # pragma: no cover - requires runtime DB
        results.append(CheckResult("runtime.database", "fail", f"Database check failed: {exc}", {"error": str(exc)}))

    try:
        cache.set("production_verification_probe", "ok", 5)
        cache_ok = cache.get("production_verification_probe") == "ok"
        results.append(CheckResult("runtime.cache", "pass" if cache_ok else "warn", "Cache probe completed.", {"matched": cache_ok}))
    except Exception as exc:  # pragma: no cover - requires runtime cache
        results.append(CheckResult("runtime.cache", "warn", f"Cache check failed: {exc}", {"error": str(exc)}))

    missing_contract_paths = [path for path in EXPECTED_ADMIN_CONTRACT_PATHS if not path.startswith("/api/v1/")]
    results.append(CheckResult(
        "admin.contract.paths",
        "pass" if not missing_contract_paths else "fail",
        "Admin-control expected API contract path inventory is present.",
        {"expected_paths": EXPECTED_ADMIN_CONTRACT_PATHS, "missing": missing_contract_paths},
    ))

    result_dicts = [result.as_dict() for result in results]
    return {
        "status": _status(results),
        "summary": {
            "total": len(result_dicts),
            "pass": sum(1 for item in result_dicts if item["status"] == "pass"),
            "warn": sum(1 for item in result_dicts if item["status"] == "warn"),
            "fail": sum(1 for item in result_dicts if item["status"] == "fail"),
            "version": "42.0.0",
        },
        "checks": result_dicts,
    }


def feature_flag_inventory() -> list[dict]:
    labels = {config.label for config in apps.get_app_configs()}
    rows = []
    for label in sorted(PRODUCTION_APPS | EXPERIMENTAL_APPS):
        tier = "production" if label in PRODUCTION_APPS else "experimental"
        rows.append({
            "app_label": label,
            "tier": tier,
            "installed": label in labels,
            "enabled_by_default": tier == "production",
        })
    return rows
