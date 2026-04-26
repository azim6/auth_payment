# Generated for django-auth-platform v15 reliability operations.
import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("billing", "0005_promotions_addons_entitlement_snapshots"),
    ]

    operations = [
        migrations.CreateModel(
            name="BillingOutboxEvent",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("event_type", models.CharField(max_length=160)),
                ("aggregate_type", models.CharField(blank=True, max_length=80)),
                ("aggregate_id", models.CharField(blank=True, max_length=120)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("processing", "Processing"), ("dispatched", "Dispatched"), ("failed", "Failed"), ("cancelled", "Cancelled")], default="pending", max_length=20)),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("headers", models.JSONField(blank=True, default=dict)),
                ("idempotency_key", models.CharField(blank=True, max_length=180)),
                ("attempts", models.PositiveIntegerField(default=0)),
                ("max_attempts", models.PositiveIntegerField(default=8)),
                ("next_attempt_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("locked_at", models.DateTimeField(blank=True, null=True)),
                ("dispatched_at", models.DateTimeField(blank=True, null=True)),
                ("last_error", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["next_attempt_at", "created_at"]},
        ),
        migrations.CreateModel(
            name="ProviderSyncState",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("provider", models.CharField(max_length=40)),
                ("resource_type", models.CharField(max_length=80)),
                ("cursor", models.CharField(blank=True, max_length=255)),
                ("status", models.CharField(choices=[("healthy", "Healthy"), ("degraded", "Degraded"), ("failing", "Failing"), ("disabled", "Disabled")], default="healthy", max_length=20)),
                ("last_started_at", models.DateTimeField(blank=True, null=True)),
                ("last_success_at", models.DateTimeField(blank=True, null=True)),
                ("last_failure_at", models.DateTimeField(blank=True, null=True)),
                ("last_error", models.TextField(blank=True)),
                ("error_count", models.PositiveIntegerField(default=0)),
                ("lag_seconds", models.PositiveIntegerField(default=0)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["provider", "resource_type"]},
        ),
        migrations.CreateModel(
            name="WebhookReplayRequest",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("status", models.CharField(choices=[("requested", "Requested"), ("replayed", "Replayed"), ("failed", "Failed"), ("cancelled", "Cancelled")], default="requested", max_length=20)),
                ("reason", models.TextField(blank=True)),
                ("replayed_at", models.DateTimeField(blank=True, null=True)),
                ("error", models.TextField(blank=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("requested_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="billing_webhook_replays_requested", to=settings.AUTH_USER_MODEL)),
                ("webhook_event", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="replay_requests", to="billing.billingwebhookevent")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="EntitlementChangeLog",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("previous_payload", models.JSONField(blank=True, default=dict)),
                ("new_payload", models.JSONField(blank=True, default=dict)),
                ("reason", models.CharField(blank=True, max_length=180)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("changed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="billing_entitlement_changes", to=settings.AUTH_USER_MODEL)),
                ("customer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="entitlement_change_logs", to="billing.billingcustomer")),
                ("snapshot", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="change_logs", to="billing.entitlementsnapshot")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddIndex(model_name="billingoutboxevent", index=models.Index(fields=["status", "next_attempt_at"], name="billing_out_status_0d7b5a_idx")),
        migrations.AddIndex(model_name="billingoutboxevent", index=models.Index(fields=["event_type", "created_at"], name="billing_out_event_t_3f4e22_idx")),
        migrations.AddIndex(model_name="billingoutboxevent", index=models.Index(fields=["aggregate_type", "aggregate_id"], name="billing_out_agg_typ_c9b1ad_idx")),
        migrations.AddIndex(model_name="billingoutboxevent", index=models.Index(fields=["idempotency_key"], name="billing_out_idempot_1851ed_idx")),
        migrations.AddConstraint(model_name="billingoutboxevent", constraint=models.UniqueConstraint(condition=models.Q(("idempotency_key", ""), _negated=True), fields=("event_type", "idempotency_key"), name="uniq_billing_outbox_event_idempotency")),
        migrations.AddIndex(model_name="providersyncstate", index=models.Index(fields=["provider", "resource_type"], name="billing_pro_provider_85cb76_idx")),
        migrations.AddIndex(model_name="providersyncstate", index=models.Index(fields=["status"], name="billing_pro_status_a6e1c1_idx")),
        migrations.AddConstraint(model_name="providersyncstate", constraint=models.UniqueConstraint(fields=("provider", "resource_type"), name="uniq_provider_sync_resource")),
        migrations.AddIndex(model_name="webhookreplayrequest", index=models.Index(fields=["status", "created_at"], name="billing_web_status_032837_idx")),
        migrations.AddIndex(model_name="webhookreplayrequest", index=models.Index(fields=["webhook_event", "status"], name="billing_web_webhook_c62528_idx")),
        migrations.AddIndex(model_name="entitlementchangelog", index=models.Index(fields=["customer", "created_at"], name="billing_ent_customer_2af6a4_idx")),
        migrations.AddIndex(model_name="entitlementchangelog", index=models.Index(fields=["reason", "created_at"], name="billing_ent_reason_99db67_idx")),
    ]
