import uuid
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("accounts", "0009_rbac_policies"),
        ("billing", "0006_reliability_ops"),
    ]

    operations = [
        migrations.CreateModel(
            name="SecurityRiskEvent",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("category", models.CharField(choices=[("auth", "Authentication"), ("billing", "Billing"), ("oauth", "OAuth/OIDC"), ("service", "Service credential"), ("admin", "Admin"), ("platform", "Platform")], max_length=24)),
                ("severity", models.CharField(choices=[("low", "Low"), ("medium", "Medium"), ("high", "High"), ("critical", "Critical")], default="low", max_length=16)),
                ("status", models.CharField(choices=[("open", "Open"), ("acknowledged", "Acknowledged"), ("resolved", "Resolved"), ("false_positive", "False positive")], default="open", max_length=24)),
                ("signal", models.CharField(help_text="Machine-readable signal code, e.g. auth.impossible_travel.", max_length=120)),
                ("score", models.PositiveSmallIntegerField(default=0, help_text="0-100 normalized risk score.")),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("user_agent", models.TextField(blank=True)),
                ("summary", models.CharField(max_length=255)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("acknowledged_at", models.DateTimeField(blank=True, null=True)),
                ("resolved_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("acknowledged_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="security_risk_events_acknowledged", to=settings.AUTH_USER_MODEL)),
                ("organization", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="security_risk_events", to="accounts.organization")),
                ("resolved_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="security_risk_events_resolved", to=settings.AUTH_USER_MODEL)),
                ("subscription", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="security_risk_events", to="billing.subscription")),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="security_risk_events", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="AccountRestriction",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("restriction_type", models.CharField(choices=[("login_block", "Login blocked"), ("api_block", "API blocked"), ("billing_block", "Billing blocked"), ("payment_review", "Payment review"), ("org_admin_lock", "Organization admin locked")], max_length=32)),
                ("reason", models.TextField()),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("starts_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("lifted_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="account_restrictions_created", to=settings.AUTH_USER_MODEL)),
                ("lifted_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="account_restrictions_lifted", to=settings.AUTH_USER_MODEL)),
                ("organization", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="account_restrictions", to="accounts.organization")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="account_restrictions", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="SecurityIncident",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("title", models.CharField(max_length=200)),
                ("severity", models.CharField(choices=[("low", "Low"), ("medium", "Medium"), ("high", "High"), ("critical", "Critical")], default="medium", max_length=16)),
                ("status", models.CharField(choices=[("open", "Open"), ("investigating", "Investigating"), ("contained", "Contained"), ("resolved", "Resolved"), ("closed", "Closed")], default="open", max_length=24)),
                ("description", models.TextField(blank=True)),
                ("containment_notes", models.TextField(blank=True)),
                ("resolution_notes", models.TextField(blank=True)),
                ("opened_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("contained_at", models.DateTimeField(blank=True, null=True)),
                ("resolved_at", models.DateTimeField(blank=True, null=True)),
                ("closed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("owner", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="owned_security_incidents", to=settings.AUTH_USER_MODEL)),
                ("related_organization", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="security_incidents", to="accounts.organization")),
                ("related_user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="security_incidents", to=settings.AUTH_USER_MODEL)),
                ("risk_events", models.ManyToManyField(blank=True, related_name="incidents", to="security_ops.securityriskevent")),
            ],
            options={"ordering": ["-opened_at"]},
        ),
        migrations.AddIndex(model_name="securityriskevent", index=models.Index(fields=["category", "severity", "status"], name="security_op_categor_bfa1d4_idx")),
        migrations.AddIndex(model_name="securityriskevent", index=models.Index(fields=["signal"], name="security_op_signal_3f4e3f_idx")),
        migrations.AddIndex(model_name="securityriskevent", index=models.Index(fields=["user", "created_at"], name="security_op_user_id_930e77_idx")),
        migrations.AddIndex(model_name="securityriskevent", index=models.Index(fields=["organization", "created_at"], name="security_op_organiz_1658fb_idx")),
        migrations.AddIndex(model_name="securityriskevent", index=models.Index(fields=["created_at"], name="security_op_created_8a82a1_idx")),
        migrations.AddIndex(model_name="accountrestriction", index=models.Index(fields=["user", "restriction_type", "lifted_at"], name="security_op_user_id_3d6c08_idx")),
        migrations.AddIndex(model_name="accountrestriction", index=models.Index(fields=["organization", "restriction_type", "lifted_at"], name="security_op_organiz_62eea6_idx")),
        migrations.AddIndex(model_name="accountrestriction", index=models.Index(fields=["expires_at"], name="security_op_expires_d4e391_idx")),
        migrations.AddIndex(model_name="securityincident", index=models.Index(fields=["severity", "status"], name="security_op_severit_cbb9c1_idx")),
        migrations.AddIndex(model_name="securityincident", index=models.Index(fields=["related_user", "status"], name="security_op_related_f5e19f_idx")),
        migrations.AddIndex(model_name="securityincident", index=models.Index(fields=["related_organization", "status"], name="security_op_related_1e54f2_idx")),
    ]
