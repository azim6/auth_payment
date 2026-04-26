from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from accounts.models import Organization, User
from billing.models import BillingCustomer, Plan, Price, Project, Subscription
from usage_billing.models import CreditGrant, Meter, MeterPrice
from usage_billing.services import aggregate_window, ingest_usage_event, rate_usage_window


class UsageBillingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="owner@example.com", password="test-password-123")
        self.org = Organization.objects.create(name="Acme", slug="acme", created_by=self.user)
        self.project = Project.objects.create(code="api", name="API")
        self.plan = Plan.objects.create(project=self.project, code="api-pro", name="API Pro")
        self.price = Price.objects.create(plan=self.plan, code="api-pro-month", amount_cents=1000)
        self.customer = BillingCustomer.objects.create(organization=self.org, billing_email="billing@example.com")
        self.subscription = Subscription.objects.create(customer=self.customer, plan=self.plan, price=self.price, status=Subscription.Status.ACTIVE)
        self.meter = Meter.objects.create(code="api.calls", name="API calls", unit="call")
        self.meter_price = MeterPrice.objects.create(meter=self.meter, plan=self.plan, code="api-calls-metered", unit_amount_cents=2, free_units=Decimal("10"))

    def test_idempotent_usage_ingestion_and_rating(self):
        now = timezone.now()
        ingest_usage_event(organization_id=self.org.id, meter_code="api.calls", quantity=Decimal("20"), idempotency_key="evt-1", user=self.user, occurred_at=now)
        ingest_usage_event(organization_id=self.org.id, meter_code="api.calls", quantity=Decimal("20"), idempotency_key="evt-1", user=self.user, occurred_at=now)
        window = aggregate_window(subscription=self.subscription, meter=self.meter, window_start=now.replace(hour=0, minute=0, second=0, microsecond=0), window_end=now.replace(hour=23, minute=59, second=59, microsecond=0))
        line = rate_usage_window(window=window, meter_price=self.meter_price, apply_credits=False)
        self.assertEqual(window.quantity, Decimal("20.000000"))
        self.assertEqual(line.billable_quantity, Decimal("10.000000"))
        self.assertEqual(line.amount_cents, 20)

    def test_credit_application_reduces_usage_charge(self):
        now = timezone.now()
        CreditGrant.objects.create(organization=self.org, original_amount_cents=50, remaining_amount_cents=50, created_by=self.user)
        ingest_usage_event(organization_id=self.org.id, meter_code="api.calls", quantity=Decimal("40"), idempotency_key="evt-2", user=self.user, occurred_at=now)
        window = aggregate_window(subscription=self.subscription, meter=self.meter, window_start=now.replace(hour=0, minute=0, second=0, microsecond=0), window_end=now.replace(hour=23, minute=59, second=59, microsecond=0))
        line = rate_usage_window(window=window, meter_price=self.meter_price, apply_credits=True)
        self.assertEqual(line.amount_cents, 10)
