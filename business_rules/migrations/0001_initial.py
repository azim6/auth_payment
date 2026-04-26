# Generated for v44 business-specific product access engine.
import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("accounts", "0009_rbac_policies"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProductAccessDecision",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("product", models.SlugField(max_length=80)),
                ("action", models.SlugField(max_length=80)),
                ("allowed", models.BooleanField(default=False)),
                ("reason", models.CharField(max_length=120)),
                ("remaining", models.IntegerField(blank=True, null=True)),
                ("limit", models.IntegerField(blank=True, null=True)),
                ("used", models.IntegerField(blank=True, null=True)),
                ("plan_codes", models.JSONField(blank=True, default=list)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("organization", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="business_access_decisions", to="accounts.organization")),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="business_access_decisions", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="ProductAccessOverride",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("product", models.SlugField(max_length=80)),
                ("action", models.SlugField(blank=True, help_text="Blank means product-wide override.", max_length=80)),
                ("entitlement_key", models.CharField(blank=True, help_text="Optional entitlement key affected by this override.", max_length=140)),
                ("effect", models.CharField(choices=[("allow", "Allow"), ("deny", "Deny"), ("limit", "Override limit")], max_length=16)),
                ("bool_value", models.BooleanField(blank=True, null=True)),
                ("int_value", models.IntegerField(blank=True, null=True)),
                ("reason", models.CharField(blank=True, max_length=255)),
                ("is_active", models.BooleanField(default=True)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="business_access_overrides_created", to=settings.AUTH_USER_MODEL)),
                ("organization", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="business_access_overrides", to="accounts.organization")),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="business_access_overrides", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="ProductUsageEvent",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("product", models.SlugField(max_length=80)),
                ("action", models.SlugField(max_length=80)),
                ("quantity", models.PositiveIntegerField(default=1)),
                ("period_key", models.CharField(blank=True, help_text="YYYY-MM, YYYY-MM-DD, or total depending on action rule.", max_length=32)),
                ("idempotency_key", models.CharField(blank=True, max_length=180)),
                ("source", models.CharField(default="api", max_length=80)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("organization", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="business_usage_events", to="accounts.organization")),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="business_usage_events", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddIndex(model_name="productaccessdecision", index=models.Index(fields=["product", "action", "allowed", "created_at"], name="business_ru_product_b06fc4_idx")),
        migrations.AddIndex(model_name="productaccessdecision", index=models.Index(fields=["user", "created_at"], name="business_ru_user_id_353030_idx")),
        migrations.AddIndex(model_name="productaccessdecision", index=models.Index(fields=["organization", "created_at"], name="business_ru_organizat_b1fa38_idx")),
        migrations.AddIndex(model_name="productaccessoverride", index=models.Index(fields=["user", "product", "action", "is_active"], name="business_ru_user_id_c88050_idx")),
        migrations.AddIndex(model_name="productaccessoverride", index=models.Index(fields=["organization", "product", "action", "is_active"], name="business_ru_organizat_410efa_idx")),
        migrations.AddIndex(model_name="productaccessoverride", index=models.Index(fields=["product", "action"], name="business_ru_product_c42b08_idx")),
        migrations.AddIndex(model_name="productaccessoverride", index=models.Index(fields=["expires_at"], name="business_ru_expires_34149f_idx")),
        migrations.AddIndex(model_name="productusageevent", index=models.Index(fields=["user", "product", "action", "period_key"], name="business_ru_user_id_1b79e9_idx")),
        migrations.AddIndex(model_name="productusageevent", index=models.Index(fields=["organization", "product", "action", "period_key"], name="business_ru_organizat_41439d_idx")),
        migrations.AddIndex(model_name="productusageevent", index=models.Index(fields=["product", "action", "created_at"], name="business_ru_product_67ec7b_idx")),
        migrations.AddIndex(model_name="productusageevent", index=models.Index(fields=["idempotency_key"], name="business_ru_idempot_301455_idx")),
        migrations.AddConstraint(model_name="productusageevent", constraint=models.UniqueConstraint(condition=models.Q(("idempotency_key__gt", "")), fields=("idempotency_key",), name="uniq_business_usage_idempotency_key")),
    ]
