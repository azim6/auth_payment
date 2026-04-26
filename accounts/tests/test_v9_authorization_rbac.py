import pytest
from django.urls import reverse

from accounts.authorization import get_user_permissions, user_has_permission
from accounts.models import Organization, OrganizationMembership, PermissionPolicy, RolePermissionGrant, User

pytestmark = pytest.mark.django_db


def make_user(email):
    return User.objects.create_user(email=email, username=email.split("@")[0], password="StrongPass123!")


def make_org(owner):
    org = Organization.objects.create(name="Acme", slug="acme", owner=owner)
    OrganizationMembership.objects.create(organization=org, user=owner, role=OrganizationMembership.Role.OWNER)
    return org


def test_owner_has_baseline_policy_management_permission():
    owner = make_user("owner@example.com")
    org = make_org(owner)
    assert user_has_permission(owner, org, "policies.manage") is True
    assert "audit.read" in get_user_permissions(owner, org)


def test_custom_policy_grant_adds_member_permission():
    owner = make_user("owner@example.com")
    member = make_user("member@example.com")
    org = make_org(owner)
    OrganizationMembership.objects.create(organization=org, user=member, role=OrganizationMembership.Role.MEMBER)
    policy = PermissionPolicy.objects.create(organization=org, code="blog.publish", name="Publish blog posts")
    RolePermissionGrant.objects.create(organization=org, role=OrganizationMembership.Role.MEMBER, policy=policy)
    assert user_has_permission(member, org, "blog.publish") is True


def test_deny_grant_removes_baseline_permission():
    owner = make_user("owner@example.com")
    org = make_org(owner)
    policy = PermissionPolicy.objects.create(organization=org, code="audit.read", name="Read audit logs")
    RolePermissionGrant.objects.create(
        organization=org,
        role=OrganizationMembership.Role.OWNER,
        policy=policy,
        effect=RolePermissionGrant.Effect.DENY,
    )
    assert user_has_permission(owner, org, "audit.read") is False
