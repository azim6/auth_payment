from decimal import Decimal
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("accounts", "0009_rbac_policies"),
        ("billing", "0006_reliability_ops"),
    ]

    operations = [
        migrations.CreateModel(
            name="Currency",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=3, unique=True)),
                ("name", models.CharField(max_length=80)),
                ("minor_unit", models.PositiveSmallIntegerField(default=2)),
                ("is_active", models.BooleanField(default=True)),
            ],
        ),
        migrations.CreateModel(
            name="TaxJurisdiction",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=40, unique=True)),
                ("name", models.CharField(max_length=160)),
                ("country_code", models.CharField(max_length=2)),
                ("region_code", models.CharField(blank=True, max_length=32)),
                ("tax_label", models.CharField(default="VAT/GST", max_length=40)),
                ("default_rate_percent", models.DecimalField(decimal_places=4, default=Decimal("0.0000"), max_digits=7)),
                ("requires_tax_id", models.BooleanField(default=False)),
                ("is_active", models.BooleanField(default=True)),
            ],
        ),
        migrations.CreateModel(
            name="Region",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=16, unique=True)),
                ("name", models.CharField(max_length=120)),
                ("country_code", models.CharField(blank=True, max_length=2)),
                ("is_tax_inclusive", models.BooleanField(default=False)),
                ("is_active", models.BooleanField(default=True)),
                ("currency", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="regions", to="tax_pricing.currency")),
            ],
        ),
        migrations.CreateModel(
            name="ExchangeRateSnapshot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("rate", models.DecimalField(decimal_places=8, max_digits=18)),
                ("source", models.CharField(default="manual", max_length=80)),
                ("effective_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("base_currency", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="fx_base_snapshots", to="tax_pricing.currency")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ("quote_currency", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="fx_quote_snapshots", to="tax_pricing.currency")),
            ],
        ),
        migrations.CreateModel(
            name="TaxRate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120)),
                ("rate_percent", models.DecimalField(decimal_places=4, max_digits=7)),
                ("product_category", models.CharField(blank=True, max_length=80)),
                ("valid_from", models.DateTimeField(default=django.utils.timezone.now)),
                ("valid_until", models.DateTimeField(blank=True, null=True)),
                ("is_reverse_charge", models.BooleanField(default=False)),
                ("is_active", models.BooleanField(default=True)),
                ("jurisdiction", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="rates", to="tax_pricing.taxjurisdiction")),
            ],
        ),
        migrations.CreateModel(
            name="TaxExemption",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("exemption_type", models.CharField(default="resale", max_length=40)),
                ("certificate_number", models.CharField(blank=True, max_length=120)),
                ("verified_at", models.DateTimeField(blank=True, null=True)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("is_active", models.BooleanField(default=True)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("jurisdiction", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="tax_pricing.taxjurisdiction")),
                ("organization", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to="accounts.organization")),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ("verified_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="verified_tax_exemptions", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="RegionalPrice",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("unit_amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("interval", models.CharField(default="month", max_length=20)),
                ("tax_behavior", models.CharField(default="exclusive", max_length=20)),
                ("provider_price_id", models.CharField(blank=True, max_length=160)),
                ("starts_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("ends_at", models.DateTimeField(blank=True, null=True)),
                ("is_active", models.BooleanField(default=True)),
                ("currency", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="tax_pricing.currency")),
                ("plan", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="regional_prices", to="billing.plan")),
                ("region", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="tax_pricing.region")),
            ],
            options={"unique_together": {("plan", "region", "currency", "interval")}},
        ),
        migrations.CreateModel(
            name="LocalizedInvoiceSetting",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("invoice_language", models.CharField(default="en", max_length=12)),
                ("invoice_prefix", models.CharField(default="INV", max_length=20)),
                ("tax_number_label", models.CharField(default="Tax ID", max_length=60)),
                ("footer_text", models.TextField(blank=True)),
                ("requires_buyer_tax_id", models.BooleanField(default=False)),
                ("requires_seller_tax_id", models.BooleanField(default=False)),
                ("region", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="invoice_settings", to="tax_pricing.region")),
            ],
        ),
        migrations.CreateModel(
            name="PriceResolutionRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("unit_amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("tax_amount", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12)),
                ("total_amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("tax_rate_percent", models.DecimalField(decimal_places=4, default=Decimal("0.0000"), max_digits=7)),
                ("tax_inclusive", models.BooleanField(default=False)),
                ("reason", models.CharField(blank=True, max_length=160)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("currency", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="tax_pricing.currency")),
                ("organization", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="accounts.organization")),
                ("plan", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="billing.plan")),
                ("region", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="tax_pricing.region")),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddIndex(
            model_name="exchangeratesnapshot",
            index=models.Index(fields=["base_currency", "quote_currency", "effective_at"], name="tax_pricin_base_cu_453d73_idx"),
        ),
    ]
