import pytest
from rest_framework.test import APIClient

from accounts.models import Organization, OrganizationMembership, User
from .models import EnterpriseIdentityProvider, SsoPolicy, VerifiedDomain


@pytest.mark.django_db
def test_org_admin_can_create_saml_idp():
    user = User.objects.create_user(email="owner@example.com", username="owner", password="StrongPassw0rd!")
    org = Organization.objects.create(name="Acme", slug="acme", owner=user)
    OrganizationMembership.objects.create(organization=org, user=user, role=OrganizationMembership.Role.OWNER)
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(
        "/api/v1/enterprise-sso/idps/",
        {
            "organization": "acme",
            "name": "Acme Okta",
            "slug": "okta",
            "protocol": "saml2",
            "entity_id": "http://www.okta.com/acme",
            "sso_url": "https://acme.okta.com/app/sso/saml",
            "default_role": "member",
        },
        format="json",
    )

    assert response.status_code == 201
    assert EnterpriseIdentityProvider.objects.filter(organization=org, slug="okta").exists()


@pytest.mark.django_db
def test_domain_verification_token_is_returned_once():
    user = User.objects.create_user(email="admin@example.com", username="admin", password="StrongPassw0rd!")
    org = Organization.objects.create(name="Example", slug="example", owner=user)
    OrganizationMembership.objects.create(organization=org, user=user, role=OrganizationMembership.Role.ADMIN)
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(
        "/api/v1/enterprise-sso/domains/",
        {"organization": "example", "domain": "example.com", "method": "dns_txt"},
        format="json",
    )

    assert response.status_code == 201
    assert response.data["raw_verification_token"]
    assert response.data["verification_record"]["type"] == "TXT"
    domain = VerifiedDomain.objects.get(organization=org, domain="example.com")
    assert domain.verification_token_hash


@pytest.mark.django_db
def test_sso_routing_requires_active_provider_for_verified_domain():
    staff = User.objects.create_user(email="staff@example.com", username="staff", password="StrongPassw0rd!", is_staff=True)
    owner = User.objects.create_user(email="owner@example.com", username="own2", password="StrongPassw0rd!")
    org = Organization.objects.create(name="Globex", slug="globex", owner=owner)
    provider = EnterpriseIdentityProvider.objects.create(
        organization=org,
        name="Globex IdP",
        slug="idp",
        protocol="saml2",
        status=EnterpriseIdentityProvider.Status.ACTIVE,
        entity_id="urn:globex:idp",
        sso_url="https://login.globex.com/saml",
        created_by=staff,
    )
    domain = VerifiedDomain.objects.create(organization=org, domain="globex.com", method="manual", status=VerifiedDomain.Status.PENDING)
    domain.mark_verified(user=staff)
    SsoPolicy.objects.create(organization=org, default_identity_provider=provider, enforcement=SsoPolicy.Enforcement.REQUIRED_FOR_DOMAIN, updated_by=staff)

    client = APIClient()
    response = client.post("/api/v1/enterprise-sso/routing/", {"email": "alice@globex.com"}, format="json")

    assert response.status_code == 200
    assert response.data["sso_required"] is True
    assert response.data["organization"] == "globex"
    assert response.data["identity_provider"]["protocol"] == "saml2"
