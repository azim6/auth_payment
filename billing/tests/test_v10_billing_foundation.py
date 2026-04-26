from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.models import Organization
from billing.models import BillingCustomer, Entitlement, Plan, Price, Project, Subscription
from billing.services import build_customer_entitlements, grant_manual_subscription


class BillingFoundationTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_superuser(email="admin@example.com", username="admin", password="strong-pass-12345")
        self.owner = User.objects.create_user(email="owner@example.com", username="owner", password="strong-pass-12345")
        self.org = Organization.objects.create(name="Acme", slug="acme", owner=self.owner)
        self.project = Project.objects.create(code="store", name="Store")
        self.plan = Plan.objects.create(project=self.project, code="store-pro", name="Store Pro", created_by=self.admin)
        self.price = Price.objects.create(plan=self.plan, code="store-pro-free", amount_cents=0, interval=Price.Interval.CUSTOM, is_custom=True, created_by=self.admin)
        Entitlement.objects.create(plan=self.plan, key="enabled", value_type=Entitlement.ValueType.BOOLEAN, bool_value=True)
        Entitlement.objects.create(plan=self.plan, key="products.max", value_type=Entitlement.ValueType.INTEGER, int_value=500)

    def test_manual_subscription_grant_builds_entitlements(self):
        subscription = grant_manual_subscription(organization=self.org, plan=self.plan, price=self.price, actor=self.admin, status=Subscription.Status.FREE)
        self.assertEqual(subscription.status, Subscription.Status.FREE)
        customer = BillingCustomer.objects.get(organization=self.org)
        payload = build_customer_entitlements(customer)
        self.assertTrue(payload["features"]["store.enabled"])
        self.assertEqual(payload["features"]["store.products.max"], 500)
