# Generated for Django Auth Platform v12.
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("billing", "0002_checkout_portal_sessions"),
    ]

    operations = [
        migrations.AddField(model_name="subscription", name="seat_limit", field=models.PositiveIntegerField(default=1)),
        migrations.AddField(model_name="subscription", name="trial_ends_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="subscription", name="grace_period_ends_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.CreateModel(
            name="SubscriptionChangeRequest",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("action", models.CharField(choices=[("change_plan", "Change plan"), ("change_quantity", "Change quantity"), ("cancel_at_period_end", "Cancel at period end"), ("cancel_now", "Cancel immediately"), ("resume", "Resume"), ("extend_trial", "Extend trial"), ("extend_grace", "Extend grace period")], max_length=40)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("applied", "Applied"), ("failed", "Failed"), ("cancelled", "Cancelled")], default="pending", max_length=20)),
                ("target_quantity", models.PositiveIntegerField(blank=True, null=True)),
                ("effective_at", models.DateTimeField(blank=True, null=True)),
                ("applied_at", models.DateTimeField(blank=True, null=True)),
                ("provider", models.CharField(default="manual", max_length=40)),
                ("provider_change_id", models.CharField(blank=True, max_length=180)),
                ("reason", models.TextField(blank=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("error", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("requested_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="billing_subscription_changes_requested", to=settings.AUTH_USER_MODEL)),
                ("subscription", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="change_requests", to="billing.subscription")),
                ("target_plan", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="subscription_change_targets", to="billing.plan")),
                ("target_price", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="subscription_change_targets", to="billing.price")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="UsageMetric",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("code", models.SlugField(max_length=120, unique=True)),
                ("name", models.CharField(max_length=180)),
                ("unit", models.CharField(default="unit", max_length=40)),
                ("aggregation", models.CharField(choices=[("sum", "Sum"), ("max", "Max"), ("last", "Last")], default="sum", max_length=16)),
                ("entitlement_key", models.CharField(help_text="Entitlement key that defines the allowed limit, e.g. api.requests.monthly.max", max_length=140)),
                ("is_active", models.BooleanField(default=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("project", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="usage_metrics", to="billing.project")),
            ],
            options={"ordering": ["code"]},
        ),
        migrations.CreateModel(
            name="UsageRecord",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("quantity", models.PositiveIntegerField(default=1)),
                ("idempotency_key", models.CharField(blank=True, max_length=180)),
                ("source", models.CharField(default="api", max_length=80)),
                ("occurred_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("customer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="usage_records", to="billing.billingcustomer")),
                ("metric", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="records", to="billing.usagemetric")),
            ],
            options={"ordering": ["-occurred_at"]},
        ),
        migrations.AddIndex(model_name="subscriptionchangerequest", index=models.Index(fields=["subscription", "status"], name="billing_sub_subscri_6dcb29_idx")),
        migrations.AddIndex(model_name="subscriptionchangerequest", index=models.Index(fields=["action", "status"], name="billing_sub_action_7eb297_idx")),
        migrations.AddIndex(model_name="subscriptionchangerequest", index=models.Index(fields=["effective_at"], name="billing_sub_effecti_03fe2e_idx")),
        migrations.AddIndex(model_name="usagemetric", index=models.Index(fields=["code"], name="billing_usa_code_56f432_idx")),
        migrations.AddIndex(model_name="usagemetric", index=models.Index(fields=["project", "is_active"], name="billing_usa_project_b25ff8_idx")),
        migrations.AddIndex(model_name="usagemetric", index=models.Index(fields=["entitlement_key"], name="billing_usa_entitle_732cfd_idx")),
        migrations.AddIndex(model_name="usagerecord", index=models.Index(fields=["customer", "metric", "occurred_at"], name="billing_usa_customer_590e29_idx")),
        migrations.AddIndex(model_name="usagerecord", index=models.Index(fields=["metric", "occurred_at"], name="billing_usa_metric__c7589b_idx")),
        migrations.AddIndex(model_name="usagerecord", index=models.Index(fields=["source"], name="billing_usa_source_27e7e0_idx")),
        migrations.AddConstraint(model_name="usagerecord", constraint=models.UniqueConstraint(fields=("customer", "metric", "idempotency_key"), name="uniq_usage_idempotency_key")),
    ]
