# Generated for django-auth-platform v8 enterprise tenancy workflow.

import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0007_privacy_compliance"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Organization",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=180)),
                ("slug", models.SlugField(max_length=80, unique=True)),
                ("plan", models.CharField(choices=[("free", "Free"), ("team", "Team"), ("business", "Business"), ("enterprise", "Enterprise")], default="free", max_length=24)),
                ("is_active", models.BooleanField(default=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("owner", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="owned_organizations", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="OrganizationMembership",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("role", models.CharField(choices=[("owner", "Owner"), ("admin", "Admin"), ("member", "Member"), ("viewer", "Viewer")], default="member", max_length=16)),
                ("is_active", models.BooleanField(default=True)),
                ("joined_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("invited_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="organization_memberships_invited", to=settings.AUTH_USER_MODEL)),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="memberships", to="accounts.organization")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="organization_memberships", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["organization", "role", "user__email"], "unique_together": {("organization", "user")}},
        ),
        migrations.CreateModel(
            name="OrganizationInvitation",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("email", models.EmailField(max_length=254)),
                ("role", models.CharField(choices=[("owner", "Owner"), ("admin", "Admin"), ("member", "Member"), ("viewer", "Viewer")], default="member", max_length=16)),
                ("token_hash", models.CharField(max_length=256, unique=True)),
                ("expires_at", models.DateTimeField()),
                ("accepted_at", models.DateTimeField(blank=True, null=True)),
                ("revoked_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("invited_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="organization_invitations_sent", to=settings.AUTH_USER_MODEL)),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="invitations", to="accounts.organization")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="TenantServiceCredential",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=150)),
                ("key_prefix", models.CharField(max_length=16, unique=True)),
                ("key_hash", models.CharField(max_length=256)),
                ("scopes", models.CharField(default="org:read members:read", max_length=255)),
                ("is_active", models.BooleanField(default=True)),
                ("last_used_at", models.DateTimeField(blank=True, null=True)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="tenant_service_credentials_created", to=settings.AUTH_USER_MODEL)),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="service_credentials", to="accounts.organization")),
            ],
            options={"ordering": ["organization", "name"]},
        ),
        migrations.AddIndex(model_name="organization", index=models.Index(fields=["slug"], name="accounts_or_slug_1a2b3c_idx")),
        migrations.AddIndex(model_name="organization", index=models.Index(fields=["owner", "created_at"], name="accounts_or_owner_4d5e6f_idx")),
        migrations.AddIndex(model_name="organization", index=models.Index(fields=["is_active", "plan"], name="accounts_or_active_7a8b9c_idx")),
        migrations.AddIndex(model_name="organizationmembership", index=models.Index(fields=["organization", "role"], name="accounts_om_org_role_1a2b_idx")),
        migrations.AddIndex(model_name="organizationmembership", index=models.Index(fields=["organization", "is_active"], name="accounts_om_org_act_3c4d_idx")),
        migrations.AddIndex(model_name="organizationmembership", index=models.Index(fields=["user", "is_active"], name="accounts_om_user_act_5e6f_idx")),
        migrations.AddIndex(model_name="organizationinvitation", index=models.Index(fields=["organization", "email"], name="accounts_oi_org_email_1a2b_idx")),
        migrations.AddIndex(model_name="organizationinvitation", index=models.Index(fields=["token_hash"], name="accounts_oi_token_3c4d_idx")),
        migrations.AddIndex(model_name="organizationinvitation", index=models.Index(fields=["expires_at"], name="accounts_oi_exp_5e6f_idx")),
        migrations.AddIndex(model_name="organizationinvitation", index=models.Index(fields=["accepted_at", "revoked_at"], name="accounts_oi_state_7a8b_idx")),
        migrations.AddIndex(model_name="tenantservicecredential", index=models.Index(fields=["organization", "is_active"], name="accounts_tsc_org_act_1a2b_idx")),
        migrations.AddIndex(model_name="tenantservicecredential", index=models.Index(fields=["key_prefix"], name="accounts_tsc_key_3c4d_idx")),
        migrations.AddIndex(model_name="tenantservicecredential", index=models.Index(fields=["expires_at"], name="accounts_tsc_exp_5e6f_idx")),
    ]
