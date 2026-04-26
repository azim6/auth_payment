# Generated for django-auth-platform v17 compliance governance foundation.
import uuid

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("accounts", "0009_rbac_policies"),
        ("security_ops", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="PolicyDocument",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("policy_type", models.CharField(choices=[("terms", "Terms of service"), ("privacy", "Privacy policy"), ("dpa", "Data processing addendum"), ("aup", "Acceptable use policy"), ("security", "Security policy"), ("billing", "Billing policy")], max_length=32)),
                ("version", models.CharField(max_length=40)),
                ("title", models.CharField(max_length=200)),
                ("body", models.TextField(blank=True)),
                ("document_url", models.URLField(blank=True)),
                ("checksum_sha256", models.CharField(blank=True, max_length=64)),
                ("requires_user_acceptance", models.BooleanField(default=True)),
                ("requires_admin_acceptance", models.BooleanField(default=False)),
                ("is_active", models.BooleanField(default=False)),
                ("published_at", models.DateTimeField(blank=True, null=True)),
                ("retired_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_policy_documents", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["policy_type", "-published_at", "-created_at"], "unique_together": {("policy_type", "version")}},
        ),
        migrations.CreateModel(
            name="AuditExport",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("export_type", models.CharField(choices=[("audit_log", "Audit log"), ("security_events", "Security events"), ("billing_events", "Billing events"), ("policy_acceptances", "Policy acceptances"), ("full_evidence", "Full evidence")], max_length=40)),
                ("status", models.CharField(choices=[("requested", "Requested"), ("ready", "Ready"), ("failed", "Failed"), ("expired", "Expired")], default="requested", max_length=20)),
                ("date_from", models.DateTimeField(blank=True, null=True)),
                ("date_to", models.DateTimeField(blank=True, null=True)),
                ("storage_uri", models.CharField(blank=True, max_length=500)),
                ("checksum_sha256", models.CharField(blank=True, max_length=64)),
                ("record_count", models.PositiveIntegerField(default=0)),
                ("error_message", models.TextField(blank=True)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("organization", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="audit_exports", to="accounts.organization")),
                ("requested_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="audit_exports", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="AdminApprovalRequest",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("action_type", models.CharField(choices=[("billing_override", "Billing override"), ("security_restriction", "Security restriction"), ("user_export", "User data export"), ("account_deletion", "Account deletion"), ("policy_publish", "Policy publish"), ("provider_replay", "Webhook/provider replay"), ("service_key_rotation", "Service key rotation")], max_length=40)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected"), ("cancelled", "Cancelled"), ("expired", "Expired")], default="pending", max_length=20)),
                ("summary", models.CharField(max_length=255)),
                ("reason", models.TextField(blank=True)),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("review_notes", models.TextField(blank=True)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("organization", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="approval_requests", to="accounts.organization")),
                ("requested_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="approval_requests_created", to=settings.AUTH_USER_MODEL)),
                ("reviewed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="approval_requests_reviewed", to=settings.AUTH_USER_MODEL)),
                ("subject_user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="approval_requests_about_user", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="UserPolicyAcceptance",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("accepted_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("user_agent", models.TextField(blank=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("organization", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="policy_acceptances", to="accounts.organization")),
                ("policy", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="acceptances", to="compliance.policydocument")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="policy_acceptances", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-accepted_at"], "unique_together": {("user", "organization", "policy")}},
        ),
        migrations.CreateModel(
            name="EvidencePack",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("pack_type", models.CharField(choices=[("security_incident", "Security incident"), ("billing_dispute", "Billing dispute"), ("customer_audit", "Customer audit"), ("compliance_review", "Compliance review")], max_length=40)),
                ("status", models.CharField(choices=[("draft", "Draft"), ("locked", "Locked"), ("exported", "Exported"), ("archived", "Archived")], default="draft", max_length=20)),
                ("title", models.CharField(max_length=220)),
                ("summary", models.TextField(blank=True)),
                ("evidence_index", models.JSONField(blank=True, default=list)),
                ("locked_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("audit_exports", models.ManyToManyField(blank=True, related_name="evidence_packs", to="compliance.auditexport")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_evidence_packs", to=settings.AUTH_USER_MODEL)),
                ("locked_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="locked_evidence_packs", to=settings.AUTH_USER_MODEL)),
                ("organization", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="evidence_packs", to="accounts.organization")),
                ("security_incident", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="evidence_packs", to="security_ops.securityincident")),
                ("subject_user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="evidence_packs", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddIndex(model_name="policydocument", index=models.Index(fields=["policy_type", "is_active"], name="compliance__policy_aa2a_idx")),
        migrations.AddIndex(model_name="policydocument", index=models.Index(fields=["version"], name="compliance__version_475a_idx")),
        migrations.AddIndex(model_name="policydocument", index=models.Index(fields=["published_at"], name="compliance__publish_e2d0_idx")),
        migrations.AddIndex(model_name="auditexport", index=models.Index(fields=["export_type", "status"], name="compliance__export__1df3_idx")),
        migrations.AddIndex(model_name="auditexport", index=models.Index(fields=["organization", "created_at"], name="compliance__organiz_06ef_idx")),
        migrations.AddIndex(model_name="auditexport", index=models.Index(fields=["expires_at"], name="compliance__expires_76ba_idx")),
        migrations.AddIndex(model_name="adminapprovalrequest", index=models.Index(fields=["action_type", "status"], name="compliance__action__d431_idx")),
        migrations.AddIndex(model_name="adminapprovalrequest", index=models.Index(fields=["requested_by", "status"], name="compliance__request_913b_idx")),
        migrations.AddIndex(model_name="adminapprovalrequest", index=models.Index(fields=["organization", "status"], name="compliance__organiz_844e_idx")),
        migrations.AddIndex(model_name="adminapprovalrequest", index=models.Index(fields=["expires_at"], name="compliance__expires_3b77_idx")),
        migrations.AddIndex(model_name="userpolicyacceptance", index=models.Index(fields=["user", "accepted_at"], name="compliance__user_id_833f_idx")),
        migrations.AddIndex(model_name="userpolicyacceptance", index=models.Index(fields=["organization", "accepted_at"], name="compliance__organiz_56e1_idx")),
        migrations.AddIndex(model_name="userpolicyacceptance", index=models.Index(fields=["policy", "accepted_at"], name="compliance__policy__57b7_idx")),
        migrations.AddIndex(model_name="evidencepack", index=models.Index(fields=["pack_type", "status"], name="compliance__pack_ty_8b0d_idx")),
        migrations.AddIndex(model_name="evidencepack", index=models.Index(fields=["organization", "created_at"], name="compliance__organiz_16a4_idx")),
        migrations.AddIndex(model_name="evidencepack", index=models.Index(fields=["subject_user", "created_at"], name="compliance__subject_07e2_idx")),
    ]
