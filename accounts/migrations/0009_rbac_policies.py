# Generated for Django Auth Platform v9 RBAC policy layer.

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("accounts", "0008_enterprise_tenancy"),
    ]

    operations = [
        migrations.CreateModel(
            name="PermissionPolicy",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("code", models.CharField(max_length=120)),
                ("name", models.CharField(max_length=180)),
                ("description", models.TextField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="permission_policies_created", to=settings.AUTH_USER_MODEL)),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="permission_policies", to="accounts.organization")),
            ],
            options={
                "ordering": ["organization", "code"],
                "indexes": [
                    models.Index(fields=["organization", "is_active"], name="accounts_pe_organiz_01f7a0_idx"),
                    models.Index(fields=["code"], name="accounts_pe_code_5506a9_idx"),
                    models.Index(fields=["expires_at"], name="accounts_pe_expires_6b9a63_idx"),
                ],
                "unique_together": {("organization", "code")},
            },
        ),
        migrations.CreateModel(
            name="RolePermissionGrant",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("role", models.CharField(choices=[("owner", "Owner"), ("admin", "Admin"), ("member", "Member"), ("viewer", "Viewer")], max_length=16)),
                ("effect", models.CharField(choices=[("allow", "Allow"), ("deny", "Deny")], default="allow", max_length=8)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="role_permission_grants_created", to=settings.AUTH_USER_MODEL)),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="role_permission_grants", to="accounts.organization")),
                ("policy", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="role_grants", to="accounts.permissionpolicy")),
            ],
            options={
                "ordering": ["organization", "role", "policy__code"],
                "indexes": [
                    models.Index(fields=["organization", "role"], name="accounts_ro_organiz_4a82d4_idx"),
                    models.Index(fields=["effect"], name="accounts_ro_effect_982130_idx"),
                ],
                "unique_together": {("organization", "role", "policy")},
            },
        ),
    ]
