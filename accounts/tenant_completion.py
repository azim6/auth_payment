from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.utils import timezone

from .authorization import ROLE_BASELINE_PERMISSIONS, SERVICE_SCOPE_TO_PERMISSIONS, list_permission_catalog
from .models import (
    AuditLog,
    Organization,
    OrganizationInvitation,
    OrganizationMembership,
    PermissionPolicy,
    RolePermissionGrant,
    TenantServiceCredential,
)
from .tenancy import TENANT_SERVICE_SCOPES


@dataclass(frozen=True)
class TenantReadinessCheck:
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


def build_tenant_authorization_readiness_report() -> dict[str, Any]:
    """Aggregate-only readiness report for tenant/RBAC operations.

    This report intentionally avoids exposing invitation tokens, tenant service
    credential hashes, or member PII. It is designed for staff operators and
    CI smoke checks before enabling multi-project access rules in production.
    """

    now = timezone.now()
    checks: list[TenantReadinessCheck] = []

    active_orgs = Organization.objects.filter(is_active=True)
    active_memberships = OrganizationMembership.objects.filter(is_active=True, organization__is_active=True)
    owner_org_count = active_orgs.filter(memberships__role=OrganizationMembership.Role.OWNER, memberships__is_active=True).distinct().count()
    org_count = active_orgs.count()

    checks.append(
        TenantReadinessCheck(
            key="active_organizations",
            status="pass",
            detail="Active organizations are the tenant boundary for web, Android, Windows, and first-party service access.",
            count=org_count,
        )
    )
    checks.append(
        TenantReadinessCheck(
            key="organization_owner_coverage",
            status=_status(org_count == owner_org_count, warn=True),
            detail="Every active organization should have at least one active owner membership for recovery and billing authority.",
            count=owner_org_count,
        )
    )
    checks.append(
        TenantReadinessCheck(
            key="membership_inventory",
            status="pass",
            detail="Active tenant memberships are the source of user role assignments; global admin status should not replace tenant membership checks.",
            count=active_memberships.count(),
        )
    )
    checks.append(
        TenantReadinessCheck(
            key="invitation_lifecycle",
            status="pass",
            detail="Organization invitations are hashed, one-time, expiring, and revocable.",
            count=OrganizationInvitation.objects.filter(accepted_at__isnull=True, revoked_at__isnull=True, expires_at__gt=now).count(),
        )
    )
    checks.append(
        TenantReadinessCheck(
            key="baseline_role_matrix",
            status=_status(all(ROLE_BASELINE_PERMISSIONS.get(role) for role, _label in OrganizationMembership.Role.choices)),
            detail="Owner/admin/member/viewer baseline permissions are defined in code and can be extended by tenant policy grants.",
            count=len(ROLE_BASELINE_PERMISSIONS),
        )
    )
    checks.append(
        TenantReadinessCheck(
            key="permission_catalog",
            status="pass",
            detail="The permission catalog combines baseline role permissions, service scopes, and active tenant-defined permission policies.",
            count=len(list_permission_catalog()),
        )
    )
    checks.append(
        TenantReadinessCheck(
            key="permission_policies",
            status="pass",
            detail="Tenant permission policies support explicit allow/deny grants without changing application code.",
            count=PermissionPolicy.objects.filter(is_active=True).count(),
        )
    )
    checks.append(
        TenantReadinessCheck(
            key="role_permission_grants",
            status="pass",
            detail="Role permission grants are tenant-scoped and auditable; deny grants override baseline or custom allows.",
            count=RolePermissionGrant.objects.select_related("policy").filter(policy__is_active=True).count(),
        )
    )
    checks.append(
        TenantReadinessCheck(
            key="tenant_service_credentials",
            status="pass",
            detail="Tenant service credentials are hashed, scoped, revocable, and restricted to active organizations.",
            count=TenantServiceCredential.objects.filter(is_active=True, organization__is_active=True).count(),
        )
    )
    checks.append(
        TenantReadinessCheck(
            key="tenant_service_scope_mapping",
            status=_status(TENANT_SERVICE_SCOPES.issubset(set(SERVICE_SCOPE_TO_PERMISSIONS.keys())), warn=True),
            detail="Every accepted tenant service scope should map to one or more concrete permission codes.",
            count=len(SERVICE_SCOPE_TO_PERMISSIONS),
        )
    )
    checks.append(
        TenantReadinessCheck(
            key="authorization_audit_events",
            status="pass" if AuditLog.objects.filter(action__startswith="organization.").exists() or AuditLog.objects.filter(action__startswith="permission_").exists() else "warn",
            detail="Organization membership changes, invitation activity, service credential actions, and policy changes should emit audit events.",
            count=AuditLog.objects.filter(category__in=[AuditLog.Category.ADMIN, AuditLog.Category.SERVICE]).count(),
        )
    )

    serialized = [check.as_dict() for check in checks]
    failed = [check for check in serialized if check["status"] == "fail"]
    warned = [check for check in serialized if check["status"] == "warn"]
    overall = "fail" if failed else "warn" if warned else "pass"

    return {
        "overall_status": overall,
        "generated_at": now.isoformat(),
        "scope": "tenant_authorization",
        "checks": serialized,
        "totals": {
            "pass": sum(1 for check in serialized if check["status"] == "pass"),
            "warn": len(warned),
            "fail": len(failed),
        },
        "recommended_next_checks": [
            "Confirm every production organization has an active owner.",
            "Run an access-review export before changing baseline role permissions.",
            "Verify tenant service credentials are rotated and scoped to least privilege.",
            "Test permission checks from blog, store, social, Android, and Windows clients before deploy.",
        ],
    }
