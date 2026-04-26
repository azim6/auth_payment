# Generated for django-auth-platform v28 SCIM provisioning foundation.
import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ScimApplication",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=180)),
                ("slug", models.SlugField(max_length=80)),
                ("status", models.CharField(choices=[("draft", "Draft"), ("active", "Active"), ("suspended", "Suspended"), ("revoked", "Revoked")], default="draft", max_length=16)),
                ("provider", models.CharField(blank=True, help_text="Okta, Azure AD, Google Workspace, OneLogin, custom, etc.", max_length=80)),
                ("token_prefix", models.CharField(blank=True, db_index=True, max_length=24)),
                ("token_hash", models.CharField(blank=True, max_length=256)),
                ("default_role", models.CharField(default="member", max_length=16)),
                ("allow_create_users", models.BooleanField(default=True)),
                ("allow_update_users", models.BooleanField(default=True)),
                ("allow_deactivate_users", models.BooleanField(default=True)),
                ("allow_group_sync", models.BooleanField(default=True)),
                ("require_verified_domain", models.BooleanField(default=True)),
                ("allowed_email_domains", models.JSONField(blank=True, default=list)),
                ("attribute_mapping", models.JSONField(blank=True, default=dict)),
                ("last_used_at", models.DateTimeField(blank=True, null=True)),
                ("activated_at", models.DateTimeField(blank=True, null=True)),
                ("revoked_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="scim_apps_created", to=settings.AUTH_USER_MODEL)),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="scim_applications", to="accounts.organization")),
            ],
            options={"ordering": ["organization__slug", "name"], "unique_together": {("organization", "slug")}},
        ),
        migrations.CreateModel(
            name="DirectoryUser",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("external_id", models.CharField(max_length=255)),
                ("user_name", models.EmailField(max_length=254)),
                ("email", models.EmailField(max_length=254)),
                ("display_name", models.CharField(blank=True, max_length=255)),
                ("given_name", models.CharField(blank=True, max_length=120)),
                ("family_name", models.CharField(blank=True, max_length=120)),
                ("status", models.CharField(choices=[("active", "Active"), ("suspended", "Suspended"), ("deprovisioned", "Deprovisioned"), ("error", "Error")], default="active", max_length=24)),
                ("active", models.BooleanField(default=True)),
                ("raw_attributes", models.JSONField(blank=True, default=dict)),
                ("last_synced_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("deprovisioned_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="directory_users", to="accounts.organization")),
                ("scim_application", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="directory_users", to="scim_provisioning.scimapplication")),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="directory_identities", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["organization__slug", "email"], "unique_together": {("organization", "external_id")}},
        ),
        migrations.CreateModel(
            name="DirectoryGroup",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("external_id", models.CharField(max_length=255)),
                ("display_name", models.CharField(max_length=255)),
                ("status", models.CharField(choices=[("active", "Active"), ("disabled", "Disabled")], default="active", max_length=16)),
                ("mapped_role", models.CharField(blank=True, max_length=16)),
                ("mapped_permissions", models.JSONField(blank=True, default=list)),
                ("raw_attributes", models.JSONField(blank=True, default=dict)),
                ("last_synced_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="directory_groups", to="accounts.organization")),
                ("scim_application", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="directory_groups", to="scim_provisioning.scimapplication")),
            ],
            options={"ordering": ["organization__slug", "display_name"], "unique_together": {("organization", "external_id")}},
        ),
        migrations.CreateModel(
            name="DeprovisioningPolicy",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("action", models.CharField(choices=[("disable_membership", "Disable tenant membership"), ("suspend_user", "Suspend local user"), ("revoke_sessions", "Revoke sessions and tokens"), ("manual_review", "Require manual review")], default="disable_membership", max_length=32)),
                ("grace_period_hours", models.PositiveIntegerField(default=0)),
                ("preserve_billing_owner", models.BooleanField(default=True)),
                ("notify_admins", models.BooleanField(default=True)),
                ("require_approval_for_owners", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("organization", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="deprovisioning_policy", to="accounts.organization")),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="deprovisioning_policies_updated", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["organization__slug"]},
        ),
        migrations.CreateModel(
            name="ScimSyncJob",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("status", models.CharField(choices=[("queued", "Queued"), ("running", "Running"), ("completed", "Completed"), ("failed", "Failed"), ("cancelled", "Cancelled")], default="queued", max_length=16)),
                ("mode", models.CharField(default="manual", max_length=32)),
                ("dry_run", models.BooleanField(default=True)),
                ("users_seen", models.PositiveIntegerField(default=0)),
                ("users_created", models.PositiveIntegerField(default=0)),
                ("users_updated", models.PositiveIntegerField(default=0)),
                ("users_deprovisioned", models.PositiveIntegerField(default=0)),
                ("groups_seen", models.PositiveIntegerField(default=0)),
                ("groups_updated", models.PositiveIntegerField(default=0)),
                ("errors", models.JSONField(blank=True, default=list)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="scim_sync_jobs", to="accounts.organization")),
                ("requested_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="scim_sync_jobs_requested", to=settings.AUTH_USER_MODEL)),
                ("scim_application", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="sync_jobs", to="scim_provisioning.scimapplication")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="DirectoryGroupMember",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("external_user_id", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("directory_user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="group_memberships", to="scim_provisioning.directoryuser")),
                ("group", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="members", to="scim_provisioning.directorygroup")),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="directory_group_members", to="accounts.organization")),
            ],
            options={"ordering": ["group__display_name", "directory_user__email"], "unique_together": {("group", "directory_user")}},
        ),
        migrations.CreateModel(
            name="ScimProvisioningEvent",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("event_type", models.CharField(choices=[("token_rotated", "Token rotated"), ("user_created", "User created"), ("user_updated", "User updated"), ("user_deactivated", "User deactivated"), ("group_created", "Group created"), ("group_updated", "Group updated"), ("group_member_synced", "Group member synced"), ("sync_started", "Sync started"), ("sync_completed", "Sync completed"), ("error", "Error")], max_length=32)),
                ("result", models.CharField(choices=[("success", "Success"), ("failure", "Failure"), ("skipped", "Skipped")], default="success", max_length=16)),
                ("external_id", models.CharField(blank=True, max_length=255)),
                ("message", models.CharField(blank=True, max_length=255)),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("user_agent", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("actor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="scim_events", to=settings.AUTH_USER_MODEL)),
                ("directory_group", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="events", to="scim_provisioning.directorygroup")),
                ("directory_user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="events", to="scim_provisioning.directoryuser")),
                ("organization", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="scim_events", to="accounts.organization")),
                ("scim_application", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="events", to="scim_provisioning.scimapplication")),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
