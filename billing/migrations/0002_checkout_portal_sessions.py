# Generated for django-auth-platform v11 payment provider integration.

import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("billing", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="CheckoutSession",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("provider", models.CharField(default="stripe", max_length=40)),
                ("provider_session_id", models.CharField(blank=True, db_index=True, max_length=220)),
                ("checkout_url", models.URLField(blank=True)),
                ("success_url", models.URLField()),
                ("cancel_url", models.URLField()),
                ("status", models.CharField(choices=[("created", "Created"), ("open", "Open"), ("completed", "Completed"), ("expired", "Expired"), ("failed", "Failed")], default="created", max_length=24)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="billing_checkout_sessions_created", to=settings.AUTH_USER_MODEL)),
                ("customer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="checkout_sessions", to="billing.billingcustomer")),
                ("plan", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="checkout_sessions", to="billing.plan")),
                ("price", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="checkout_sessions", to="billing.price")),
            ],
            options={
                "ordering": ["-created_at"],
                "indexes": [models.Index(fields=["customer", "status"], name="billing_che_customer_9f2355_idx"), models.Index(fields=["provider", "provider_session_id"], name="billing_che_provider_663a4e_idx"), models.Index(fields=["created_by", "created_at"], name="billing_che_created_0880ca_idx")],
            },
        ),
        migrations.CreateModel(
            name="CustomerPortalSession",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("provider", models.CharField(default="stripe", max_length=40)),
                ("provider_session_id", models.CharField(blank=True, db_index=True, max_length=220)),
                ("portal_url", models.URLField()),
                ("return_url", models.URLField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="billing_portal_sessions_created", to=settings.AUTH_USER_MODEL)),
                ("customer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="portal_sessions", to="billing.billingcustomer")),
            ],
            options={
                "ordering": ["-created_at"],
                "indexes": [models.Index(fields=["customer", "created_at"], name="billing_cus_customer_12c9ac_idx"), models.Index(fields=["provider", "provider_session_id"], name="billing_cus_provider_bcac23_idx")],
            },
        ),
    ]
