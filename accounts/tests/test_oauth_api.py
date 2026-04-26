import hashlib
import base64

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.oauth import generate_client_secret, hash_client_secret
from accounts.models import OAuthClient


User = get_user_model()


@override_settings(ACCOUNT_EMAIL_DELIVERY="sync", CELERY_TASK_ALWAYS_EAGER=True)
class OAuthApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_superuser(
            email="admin@example.com",
            username="admin",
            password="StrongPassword123!",
        )
        self.user = User.objects.create_user(
            email="user@example.com",
            username="user",
            password="StrongPassword123!",
        )

    def test_admin_can_register_confidential_client(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            reverse("oauth-clients"),
            {
                "name": "Blog App",
                "is_confidential": True,
                "redirect_uris": ["https://blog.example.com/auth/callback"],
                "allowed_scopes": "openid profile email",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data["client_id"].startswith("cli_"))
        self.assertTrue(response.data["client_secret"].startswith("sec_"))

    def test_authorization_code_can_be_exchanged_for_tokens(self):
        raw_secret = generate_client_secret()
        oauth_client = OAuthClient.objects.create(
            name="Desktop App",
            client_id="cli_test",
            client_secret_hash=hash_client_secret(raw_secret),
            is_confidential=True,
            redirect_uris="https://desktop.example.com/callback",
            allowed_scopes="openid profile email",
        )
        self.client.force_authenticate(self.user)
        auth_response = self.client.post(
            reverse("oauth-authorize"),
            {
                "response_type": "code",
                "client_id": oauth_client.client_id,
                "redirect_uri": "https://desktop.example.com/callback",
                "scope": "openid profile email",
                "state": "abc123",
            },
            format="json",
        )
        self.assertEqual(auth_response.status_code, 201)
        raw_code = auth_response.data["code"]

        self.client.force_authenticate(None)
        token_response = self.client.post(
            reverse("oauth-token"),
            {
                "grant_type": "authorization_code",
                "code": raw_code,
                "redirect_uri": "https://desktop.example.com/callback",
                "client_id": oauth_client.client_id,
                "client_secret": raw_secret,
            },
            format="json",
        )
        self.assertEqual(token_response.status_code, 200)
        self.assertIn("access_token", token_response.data)
        self.assertIn("refresh_token", token_response.data)
        self.assertIn("id_token", token_response.data)

    def test_public_client_uses_pkce(self):
        verifier = "correct-horse-battery-staple-verifier"
        digest = hashlib.sha256(verifier.encode("ascii")).digest()
        challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
        oauth_client = OAuthClient.objects.create(
            name="Android App",
            client_id="cli_android",
            is_confidential=False,
            redirect_uris="com.example.app://auth/callback",
            allowed_scopes="openid profile email",
        )
        self.client.force_authenticate(self.user)
        auth_response = self.client.post(
            reverse("oauth-authorize"),
            {
                "response_type": "code",
                "client_id": oauth_client.client_id,
                "redirect_uri": "com.example.app://auth/callback",
                "scope": "openid profile email",
                "code_challenge": challenge,
                "code_challenge_method": "S256",
            },
            format="json",
        )
        self.assertEqual(auth_response.status_code, 201)

        self.client.force_authenticate(None)
        token_response = self.client.post(
            reverse("oauth-token"),
            {
                "grant_type": "authorization_code",
                "code": auth_response.data["code"],
                "redirect_uri": "com.example.app://auth/callback",
                "client_id": oauth_client.client_id,
                "code_verifier": verifier,
            },
            format="json",
        )
        self.assertEqual(token_response.status_code, 200)
