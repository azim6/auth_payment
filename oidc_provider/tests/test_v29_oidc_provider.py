from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import OAuthClient
from oidc_provider.models import OAuthScopeDefinition, OidcSigningKey


class V29OidcProviderTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="admin@example.com",
            username="admin",
            password="StrongPass12345!",
            is_staff=True,
        )
        self.client_api = APIClient()
        self.client_api.force_authenticate(self.user)
        self.oauth_client = OAuthClient.objects.create(
            owner=self.user,
            name="First Party Web",
            client_id="web_client_1",
            is_confidential=True,
            redirect_uris="https://app.example.com/callback",
            allowed_scopes="openid profile email",
        )

    def test_staff_can_create_scope_definition(self):
        response = self.client_api.post(
            "/api/v1/oidc/scopes/",
            {
                "name": "billing.read",
                "display_name": "Read billing",
                "sensitivity": "medium",
                "requires_consent": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(OAuthScopeDefinition.objects.filter(name="billing.read").exists())

    def test_jwks_only_exposes_publishable_keys(self):
        OidcSigningKey.objects.create(
            kid="active-key",
            algorithm="RS256",
            status="active",
            public_jwk={"kty": "RSA", "n": "example", "e": "AQAB"},
            created_by=self.user,
        )
        OidcSigningKey.objects.create(kid="retired-key", algorithm="RS256", status="retired", created_by=self.user)
        response = self.client_api.get("/api/v1/oidc/jwks/")
        self.assertEqual(response.status_code, 200)
        kids = [key["kid"] for key in response.data["keys"]]
        self.assertIn("active-key", kids)
        self.assertNotIn("retired-key", kids)

    def test_consent_evaluation_reports_missing_scopes(self):
        OAuthScopeDefinition.objects.create(name="profile", display_name="Profile", requires_consent=True)
        response = self.client_api.post(
            "/api/v1/oidc/consent/evaluate/",
            {"client_id": self.oauth_client.client_id, "scopes": ["profile"]},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["requires_consent"])
        self.assertIn("profile", response.data["missing_scopes"])
