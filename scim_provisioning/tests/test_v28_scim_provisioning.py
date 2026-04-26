from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import Organization, OrganizationMembership
from scim_provisioning.models import DirectoryGroup, DirectoryUser, ScimApplication


class ScimProvisioningTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(email="admin@example.com", password="pass-1234567890", is_staff=True)
        self.org = Organization.objects.create(name="Acme", slug="acme")
        OrganizationMembership.objects.create(organization=self.org, user=self.admin, role=OrganizationMembership.Role.OWNER)
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    def test_admin_can_create_scim_application_and_receive_one_time_token(self):
        response = self.client.post(
            "/api/v1/scim/applications/",
            {
                "organization": "acme",
                "name": "Okta SCIM",
                "slug": "okta",
                "provider": "okta",
                "default_role": "member",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertIn("raw_token", response.data)
        app = ScimApplication.objects.get(slug="okta")
        self.assertTrue(app.token_hash)
        self.assertNotEqual(app.token_hash, response.data["raw_token"])

    def test_scim_token_can_upsert_user(self):
        app = ScimApplication.objects.create(organization=self.org, name="Azure AD", slug="azure", status=ScimApplication.Status.ACTIVE)
        raw = app.rotate_token()
        response = self.client.post(
            f"/api/v1/scim/v2/{app.id}/Users/upsert/",
            {
                "external_id": "00u123",
                "user_name": "worker@example.com",
                "email": "worker@example.com",
                "display_name": "Worker One",
                "active": True,
            },
            HTTP_AUTHORIZATION=f"Bearer {raw}",
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(DirectoryUser.objects.filter(organization=self.org, external_id="00u123").exists())

    def test_scim_token_can_sync_group_membership(self):
        app = ScimApplication.objects.create(organization=self.org, name="Okta", slug="okta", status=ScimApplication.Status.ACTIVE)
        raw = app.rotate_token()
        DirectoryUser.objects.create(organization=self.org, scim_application=app, external_id="u1", user_name="a@example.com", email="a@example.com")
        response = self.client.post(
            f"/api/v1/scim/v2/{app.id}/Groups/upsert/",
            {
                "external_id": "g1",
                "display_name": "Admins",
                "mapped_role": "admin",
                "member_external_ids": ["u1"],
            },
            HTTP_AUTHORIZATION=f"Bearer {raw}",
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        group = DirectoryGroup.objects.get(organization=self.org, external_id="g1")
        self.assertEqual(group.mapped_role, "admin")
        self.assertEqual(group.members.count(), 1)
