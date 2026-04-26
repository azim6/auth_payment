from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from django.utils import timezone

from .models import Organization, OrganizationMembership, PermissionPolicy, RolePermissionGrant, TenantServiceCredential


ROLE_BASELINE_PERMISSIONS = {
    OrganizationMembership.Role.OWNER: {
        "org.read", "org.update", "org.delete",
        "members.read", "members.invite", "members.update", "members.remove",
        "billing.manage", "service_credentials.manage", "audit.read",
        "policies.read", "policies.manage",
    },
    OrganizationMembership.Role.ADMIN: {
        "org.read", "org.update",
        "members.read", "members.invite", "members.update",
        "service_credentials.manage", "audit.read",
        "policies.read",
    },
    OrganizationMembership.Role.MEMBER: {"org.read", "members.read"},
    OrganizationMembership.Role.VIEWER: {"org.read"},
}

SERVICE_SCOPE_TO_PERMISSIONS = {
    "org:read": {"org.read"},
    "org:write": {"org.update"},
    "members:read": {"members.read"},
    "members:write": {"members.invite", "members.update", "members.remove"},
    "users:read": {"members.read"},
    "audit:read": {"audit.read"},
    "policies:read": {"policies.read"},
    "policies:write": {"policies.manage"},
}


def normalize_permission_code(code: str) -> str:
    return code.strip().lower().replace(":", ".")


def get_role_permissions(organization: Organization, role: str) -> set[str]:
    permissions = set(ROLE_BASELINE_PERMISSIONS.get(role, set()))
    now = timezone.now()
    grants = RolePermissionGrant.objects.filter(
        organization=organization,
        role=role,
        policy__is_active=True,
    ).select_related("policy")
    for grant in grants:
        policy = grant.policy
        if policy.expires_at and policy.expires_at <= now:
            continue
        code = normalize_permission_code(policy.code)
        if grant.effect == RolePermissionGrant.Effect.ALLOW:
            permissions.add(code)
        elif grant.effect == RolePermissionGrant.Effect.DENY:
            permissions.discard(code)
    return permissions


def get_user_permissions(user, organization: Organization) -> set[str]:
    membership = OrganizationMembership.objects.filter(
        organization=organization,
        user=user,
        is_active=True,
    ).first()
    if not membership:
        return set()
    return get_role_permissions(organization, membership.role)


def user_has_permission(user, organization: Organization, permission_code: str) -> bool:
    return normalize_permission_code(permission_code) in get_user_permissions(user, organization)


def get_service_permissions(credential: TenantServiceCredential) -> set[str]:
    permissions: set[str] = set()
    for scope in credential.scope_set:
        permissions.update(SERVICE_SCOPE_TO_PERMISSIONS.get(scope, set()))
    return permissions


def service_has_permission(credential: TenantServiceCredential, permission_code: str) -> bool:
    return normalize_permission_code(permission_code) in get_service_permissions(credential)


def list_permission_catalog() -> list[dict]:
    codes = set()
    for values in ROLE_BASELINE_PERMISSIONS.values():
        codes.update(values)
    for values in SERVICE_SCOPE_TO_PERMISSIONS.values():
        codes.update(values)
    for code in PermissionPolicy.objects.filter(is_active=True).values_list("code", flat=True):
        codes.add(normalize_permission_code(code))
    return [{"code": code} for code in sorted(codes)]
