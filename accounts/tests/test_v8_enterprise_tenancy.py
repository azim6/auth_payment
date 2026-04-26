from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import Organization, OrganizationInvitation, OrganizationMembership, TenantServiceCredential, User


pytestmark = pytest.mark.django_db


def make_user(email="owner@example.com", username="owner"):
    return User.objects.create_user(email=email, username=username, password="StrongPass123!")


def authenticated_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def test_user_can_create_organization_and_becomes_owner():
    user = make_user()
    client = authenticated_client(user)

    response = client.post(reverse("organizations"), {"name": "Acme", "slug": "acme", "plan": "team"}, format="json")

    assert response.status_code == 201
    org = Organization.objects.get(slug="acme")
    membership = OrganizationMembership.objects.get(organization=org, user=user)
    assert membership.role == OrganizationMembership.Role.OWNER


def test_admin_can_invite_member_and_member_can_accept():
    owner = make_user()
    member = make_user(email="member@example.com", username="member")
    org = Organization.objects.create(name="Acme", slug="acme", owner=owner)
    OrganizationMembership.objects.create(organization=org, user=owner, role=OrganizationMembership.Role.OWNER)

    owner_client = authenticated_client(owner)
    invite_response = owner_client.post(
        reverse("organization-invitations", kwargs={"slug": "acme"}),
        {
            "email": member.email,
            "role": "member",
            "expires_at": (timezone.now() + timedelta(days=7)).isoformat(),
        },
        format="json",
    )

    assert invite_response.status_code == 201
    raw_token = invite_response.data["raw_token"]
    assert raw_token.startswith("invite_")

    member_client = authenticated_client(member)
    accept_response = member_client.post(reverse("organization-invitation-accept"), {"token": raw_token}, format="json")

    assert accept_response.status_code == 200
    assert OrganizationInvitation.objects.get(email=member.email).accepted_at is not None
    assert OrganizationMembership.objects.filter(organization=org, user=member, role="member", is_active=True).exists()


def test_admin_can_create_tenant_service_credential_once_raw_key():
    owner = make_user()
    org = Organization.objects.create(name="Acme", slug="acme", owner=owner)
    OrganizationMembership.objects.create(organization=org, user=owner, role=OrganizationMembership.Role.OWNER)
    client = authenticated_client(owner)

    response = client.post(
        reverse("tenant-service-credentials", kwargs={"slug": "acme"}),
        {"name": "store-sync", "scopes": "org:read members:read users:read"},
        format="json",
    )

    assert response.status_code == 201
    assert response.data["raw_key"].startswith("tsvc_")
    credential = TenantServiceCredential.objects.get(name="store-sync")
    assert credential.organization == org
    assert credential.key_hash
