from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.models import Organization, OrganizationMembership
from notifications.models import NotificationChannel, NotificationDelivery, NotificationTemplate
from notifications.services import create_notification_event, enqueue_deliveries


class NotificationInfrastructureTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(email="owner@example.com", username="owner", password="StrongPass12345")
        self.org = Organization.objects.create(name="Acme", slug="acme", owner=self.user)
        OrganizationMembership.objects.create(organization=self.org, user=self.user, role="owner")
        NotificationTemplate.objects.create(key="billing.invoice_paid", channel=NotificationChannel.EMAIL, subject_template="Invoice {{ amount }} paid", body_template="Thanks {{ user.email }}")

    def test_event_creates_email_delivery_from_template(self):
        event = create_notification_event(event_type="billing.invoice_paid", topic="billing", payload={"amount": "$20"}, organization=self.org, user=self.user)
        deliveries = enqueue_deliveries(event, channels=[NotificationChannel.EMAIL])
        self.assertEqual(len(deliveries), 1)
        delivery = NotificationDelivery.objects.get(id=deliveries[0].id)
        self.assertEqual(delivery.recipient, "owner@example.com")
        self.assertIn("$20", delivery.subject)
        self.assertEqual(delivery.status, NotificationDelivery.Status.PENDING)

    def test_idempotency_key_reuses_event(self):
        first = create_notification_event(event_type="security.alert", topic="security", organization=self.org, user=self.user, idempotency_key="evt-1")
        second = create_notification_event(event_type="security.alert", topic="security", organization=self.org, user=self.user, idempotency_key="evt-1")
        self.assertEqual(first.id, second.id)
