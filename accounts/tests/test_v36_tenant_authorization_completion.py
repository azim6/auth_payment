import pytest
from django.urls import reverse

from accounts.models import Organization, OrganizationMembership, PermissionPolicy, RolePermissionGrant, TenantServiceCredential, User
from accounts.tenant_completion import build_tenant_authorization_readiness_report
from accounts.tenancy import generate_tenant_service_key, hash_tenant_service_key, tenant_service_key_prefix

pytestmark = pytest.mark.django_db


def make_user(email, *, is_staff=False):
    return User.objects.create_user(email=email, username=email.split("@")[0], password="StrongPass123!", is_staff=is_staff)


def make_org(owner):
    org = Organization.objects.create(name="Acme", slug="acme", owner=owner)
    OrganizationMembership.objects.create(organization=org, user=owner, role=OrganizationMembership.Role.OWNER)
    return org


def test_tenant_authorization_readiness_report_tracks_core_counts():
    owner = make_user("owner@example.com")
    org = make_org(owner)
    policy = PermissionPolicy.objects.create(organization=org, code="blog.posts.create", name="Create blog posts")
    RolePermissionGrant.objects.create(organization=org, role=OrganizationMembership.Role.MEMBER, policy=policy)
    raw_key = generate_tenant_service_key()
    TenantServiceCredential.objects.create(
        organization=org,
        created_by=owner,
        name="Blog worker",
        key_prefix=tenant_service_key_prefix(raw_key),
        key_hash=hash_tenant_service_key(raw_key),
        scopes="org:read members:read",
    )

    report = build_tenant_authorization_readiness_report()

    assert report["scope"] == "tenant_authorization"
    assert report["overall_status"] in {"pass", "warn"}
    checks = {check["key"]: check for check in report["checks"]}
    assert checks["active_organizations"]["count"] == 1
    assert checks["organization_owner_coverage"]["count"] == 1
    assert checks["permission_policies"]["count"] == 1
    assert checks["role_permission_grants"]["count"] == 1
    assert checks["tenant_service_credentials"]["count"] == 1


def test_tenant_readiness_endpoint_is_staff_only(api_client):
    user = make_user("user@example.com")
    api_client.force_authenticate(user=user)
    response = api_client.get(reverse("tenant-authorization-readiness"))
    assert response.status_code == 403


def test_staff_can_read_tenant_readiness_endpoint(api_client):
    staff = make_user("staff@example.com", is_staff=True)
    api_client.force_authenticate(user=staff)
    response = api_client.get(reverse("tenant-authorization-readiness"))
    assert response.status_code == 200
    assert response.data["scope"] == "tenant_authorization"
