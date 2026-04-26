from django.contrib.auth import get_user_model
from django.test import TestCase

from data_governance.models import DataAsset, DataCategory, LegalHold, RetentionPolicy
from data_governance.services import create_inventory_snapshot, plan_retention_job, release_legal_hold, run_retention_job


class DataGovernanceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(email="admin@example.com", password="StrongPassword123!", is_staff=True)

    def test_inventory_snapshot_counts_assets_and_pii(self):
        category = DataCategory.objects.create(key="email-address", name="Email address", is_pii=True, sensitivity="confidential")
        asset = DataAsset.objects.create(key="accounts-user", name="User model", app_label="accounts", model_name="User", contains_pii=True)
        asset.categories.add(category)
        snapshot = create_inventory_snapshot(self.user)
        self.assertEqual(snapshot.asset_count, 1)
        self.assertEqual(snapshot.pii_asset_count, 1)
        self.assertEqual(snapshot.restricted_asset_count, 0)

    def test_retention_job_is_blocked_by_active_legal_hold(self):
        asset = DataAsset.objects.create(key="billing-invoices", name="Invoices", app_label="billing", contains_payment_data=True)
        policy = RetentionPolicy.objects.create(key="invoice-retention", name="Invoice retention", retention_days=2555, action="archive")
        policy.assets.add(asset)
        LegalHold.objects.create(scope=LegalHold.Scope.GLOBAL, reason="Regulatory review", created_by=self.user)
        job = plan_retention_job(policy, self.user, dry_run=True)
        updated = run_retention_job(job)
        self.assertEqual(updated.status, updated.Status.BLOCKED)
        self.assertEqual(updated.blocked_count, 1)

    def test_legal_hold_release(self):
        hold = LegalHold.objects.create(scope=LegalHold.Scope.GLOBAL, reason="Investigation", created_by=self.user)
        released = release_legal_hold(hold, self.user)
        self.assertEqual(released.status, LegalHold.Status.RELEASED)
        self.assertIsNotNone(released.released_at)
