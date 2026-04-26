from django.contrib.auth import get_user_model
from django.test import TestCase

from customer_portal.models import PortalActivityLog, PortalProfileSettings
from customer_portal.services import create_portal_api_key, find_valid_portal_api_key, validate_portal_scopes


class CustomerPortalTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(email="portal@example.com", password="StrongPass12345!")

    def test_profile_settings_are_user_scoped(self):
        settings = PortalProfileSettings.objects.create(user=self.user, display_name="Portal User")
        self.assertEqual(settings.user, self.user)
        self.assertEqual(settings.display_name, "Portal User")

    def test_portal_api_key_is_hashed_and_validated(self):
        key, raw = create_portal_api_key(user=self.user, name="Local dev", scopes="profile:read billing:read")
        self.assertTrue(raw.startswith("cpak_"))
        self.assertNotEqual(key.key_hash, raw)
        self.assertEqual(find_valid_portal_api_key(raw), key)

    def test_invalid_scope_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_portal_scopes("profile:read admin:root")

    def test_activity_log_records_customer_visible_events(self):
        event = PortalActivityLog.objects.create(
            user=self.user,
            domain=PortalActivityLog.Domain.AUTH,
            event_type="test.event",
            title="Test event",
        )
        self.assertEqual(event.user, self.user)
        self.assertEqual(event.domain, "auth")
