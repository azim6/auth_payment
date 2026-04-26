# Generated for django-auth-platform v31 usage billing foundation.
import uuid
from decimal import Decimal

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("accounts", "0001_initial"),
        ("billing", "0006_reliability_ops"),
    ]

    operations = [
        migrations.CreateModel(
            name="Meter",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("code", models.SlugField(max_length=120, unique=True)),
                ("name", models.CharField(max_length=180)),
                ("description", models.TextField(blank=True)),
                ("unit", models.CharField(default="unit", max_length=40)),
                ("aggregation", models.CharField(choices=[("sum", "Sum"), ("max", "Maximum"), ("last", "Last value"), ("unique", "Unique count")], default="sum", max_length=16)),
                ("is_active", models.BooleanField(default=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["code"]},
        ),
        migrations.CreateModel(
            name="MeterPrice",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("code", models.SlugField(max_length=140, unique=True)),
                ("pricing_model", models.CharField(choices=[("per_unit", "Per unit"), ("tiered", "Tiered"), ("package", "Package"), ("free_allowance", "Free allowance")], default="per_unit", max_length=32)),
                ("currency", models.CharField(default="USD", max_length=3)),
                ("unit_amount_cents", models.PositiveIntegerField(default=0)),
                ("free_units", models.DecimalField(decimal_places=6, default=Decimal("0"), max_digits=18)),
                ("tier_config", models.JSONField(blank=True, default=list)),
                ("is_active", models.BooleanField(default=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("addon", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="meter_prices", to="billing.addon")),
                ("meter", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="prices", to="usage_billing.meter")),
                ("plan", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="meter_prices", to="billing.plan")),
            ],
            options={"ordering": ["meter__code", "code"]},
        ),
        migrations.CreateModel(
            name="UsageEvent",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("quantity", models.DecimalField(decimal_places=6, default=Decimal("1"), max_digits=18)),
                ("occurred_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("idempotency_key", models.CharField(max_length=180)),
                ("source", models.CharField(default="api", max_length=80)),
                ("attributes", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("meter", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="events", to="usage_billing.meter")),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="usage_events", to="accounts.organization")),
                ("subscription", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="usage_events", to="billing.subscription")),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="usage_events", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-occurred_at"]},
        ),
        migrations.CreateModel(
            name="UsageAggregationWindow",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("window_start", models.DateTimeField()),
                ("window_end", models.DateTimeField()),
                ("quantity", models.DecimalField(decimal_places=6, default=Decimal("0"), max_digits=18)),
                ("status", models.CharField(choices=[("open", "Open"), ("finalized", "Finalized"), ("invoiced", "Invoiced"), ("void", "Void")], default="open", max_length=20)),
                ("finalized_at", models.DateTimeField(blank=True, null=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("meter", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="windows", to="usage_billing.meter")),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="usage_windows", to="accounts.organization")),
                ("subscription", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="usage_windows", to="billing.subscription")),
            ],
            options={"ordering": ["-window_start"]},
        ),
        migrations.CreateModel(
            name="RatedUsageLine",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("quantity", models.DecimalField(decimal_places=6, max_digits=18)),
                ("free_units_applied", models.DecimalField(decimal_places=6, default=Decimal("0"), max_digits=18)),
                ("billable_quantity", models.DecimalField(decimal_places=6, default=Decimal("0"), max_digits=18)),
                ("currency", models.CharField(default="USD", max_length=3)),
                ("amount_cents", models.IntegerField(default=0)),
                ("status", models.CharField(choices=[("draft", "Draft"), ("ready", "Ready"), ("invoiced", "Invoiced"), ("failed", "Failed")], default="draft", max_length=20)),
                ("rating_details", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("invoice", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="usage_lines", to="billing.invoice")),
                ("meter_price", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="rated_lines", to="usage_billing.meterprice")),
                ("window", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="rated_line", to="usage_billing.usageaggregationwindow")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="CreditGrant",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("currency", models.CharField(default="USD", max_length=3)),
                ("original_amount_cents", models.PositiveIntegerField()),
                ("remaining_amount_cents", models.PositiveIntegerField()),
                ("reason", models.CharField(blank=True, max_length=140)),
                ("status", models.CharField(choices=[("active", "Active"), ("expired", "Expired"), ("depleted", "Depleted"), ("void", "Void")], default="active", max_length=20)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="credit_grants_created", to=settings.AUTH_USER_MODEL)),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="credit_grants", to="accounts.organization")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="CreditApplication",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("amount_cents", models.PositiveIntegerField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("credit_grant", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="applications", to="usage_billing.creditgrant")),
                ("rated_line", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="credit_applications", to="usage_billing.ratedusageline")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="UsageReconciliationRun",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("provider", models.CharField(default="stripe", max_length=40)),
                ("window_start", models.DateTimeField()),
                ("window_end", models.DateTimeField()),
                ("status", models.CharField(choices=[("planned", "Planned"), ("running", "Running"), ("completed", "Completed"), ("failed", "Failed")], default="planned", max_length=20)),
                ("local_total_cents", models.IntegerField(default=0)),
                ("provider_total_cents", models.IntegerField(default=0)),
                ("mismatch_count", models.PositiveIntegerField(default=0)),
                ("report", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="usage_reconciliations_created", to=settings.AUTH_USER_MODEL)),
                ("organization", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="usage_reconciliation_runs", to="accounts.organization")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddIndex(model_name="meter", index=models.Index(fields=["code"], name="usage_billi_code_0e255d_idx")),
        migrations.AddIndex(model_name="meter", index=models.Index(fields=["is_active"], name="usage_billi_is_acti_6c4f93_idx")),
        migrations.AddConstraint(model_name="usageevent", constraint=models.UniqueConstraint(fields=("organization", "meter", "idempotency_key"), name="uniq_usage_event_idempotency")),
        migrations.AddConstraint(model_name="usageaggregationwindow", constraint=models.UniqueConstraint(fields=("subscription", "meter", "window_start", "window_end"), name="uniq_usage_window")),
    ]
