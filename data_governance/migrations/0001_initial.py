# Generated for django-auth-platform v22 data governance infrastructure.
import uuid
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL), ("accounts", "0009_rbac_policies")]
    operations = [
        migrations.CreateModel(name="DataCategory", fields=[
            ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
            ("key", models.SlugField(max_length=120, unique=True)), ("name", models.CharField(max_length=160)),
            ("description", models.TextField(blank=True)), ("sensitivity", models.CharField(choices=[("public", "Public"), ("internal", "Internal"), ("confidential", "Confidential"), ("restricted", "Restricted")], default="internal", max_length=24)),
            ("processing_basis", models.CharField(choices=[("contract", "Contract"), ("consent", "Consent"), ("legitimate_interest", "Legitimate interest"), ("legal_obligation", "Legal obligation"), ("security", "Security")], default="contract", max_length=32)),
            ("is_pii", models.BooleanField(default=False)), ("is_payment_data", models.BooleanField(default=False)),
            ("default_retention_days", models.PositiveIntegerField(default=365)), ("default_anonymization_strategy", models.CharField(default="hash_or_null", max_length=80)),
            ("owner_team", models.CharField(blank=True, max_length=120)), ("status", models.CharField(choices=[("draft", "Draft"), ("active", "Active"), ("paused", "Paused"), ("retired", "Retired")], default="active", max_length=16)),
            ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
        ], options={"ordering": ["key"]}),
        migrations.CreateModel(name="DataAsset", fields=[
            ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
            ("key", models.SlugField(max_length=160, unique=True)), ("name", models.CharField(max_length=180)),
            ("asset_type", models.CharField(choices=[("model", "Django model"), ("table", "Database table"), ("api", "API endpoint"), ("provider", "Payment/notification provider object"), ("file", "File/export storage"), ("log", "Log/observability stream")], default="model", max_length=24)),
            ("app_label", models.CharField(blank=True, max_length=80)), ("model_name", models.CharField(blank=True, max_length=120)), ("storage_location", models.CharField(blank=True, max_length=240)),
            ("contains_pii", models.BooleanField(default=False)), ("contains_payment_data", models.BooleanField(default=False)), ("encryption_required", models.BooleanField(default=True)), ("access_review_required", models.BooleanField(default=True)),
            ("owner_team", models.CharField(blank=True, max_length=120)), ("status", models.CharField(choices=[("draft", "Draft"), ("active", "Active"), ("paused", "Paused"), ("retired", "Retired")], default="active", max_length=16)),
            ("metadata", models.JSONField(blank=True, default=dict)), ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ("categories", models.ManyToManyField(blank=True, related_name="assets", to="data_governance.datacategory")),
        ], options={"ordering": ["app_label", "key"]}),
        migrations.CreateModel(name="RetentionPolicy", fields=[
            ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
            ("key", models.SlugField(max_length=160, unique=True)), ("name", models.CharField(max_length=180)), ("description", models.TextField(blank=True)),
            ("retention_days", models.PositiveIntegerField(default=365)), ("action", models.CharField(choices=[("delete", "Delete"), ("anonymize", "Anonymize"), ("archive", "Archive"), ("review", "Review")], default="anonymize", max_length=16)),
            ("grace_days", models.PositiveIntegerField(default=30)), ("legal_hold_exempt", models.BooleanField(default=True)), ("is_active", models.BooleanField(default=True)),
            ("owner_team", models.CharField(blank=True, max_length=120)), ("runbook_url", models.CharField(blank=True, max_length=500)),
            ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ("assets", models.ManyToManyField(blank=True, related_name="retention_policies", to="data_governance.dataasset")),
            ("categories", models.ManyToManyField(blank=True, related_name="retention_policies", to="data_governance.datacategory")),
            ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="retention_policies_created", to=settings.AUTH_USER_MODEL)),
        ], options={"ordering": ["key"]}),
        migrations.CreateModel(name="LegalHold", fields=[
            ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
            ("scope", models.CharField(choices=[("user", "User"), ("organization", "Organization"), ("category", "Data category"), ("global", "Global")], max_length=24)),
            ("reason", models.CharField(max_length=240)), ("description", models.TextField(blank=True)),
            ("status", models.CharField(choices=[("active", "Active"), ("released", "Released")], default="active", max_length=16)),
            ("starts_at", models.DateTimeField(default=django.utils.timezone.now)), ("ends_at", models.DateTimeField(blank=True, null=True)),
            ("released_at", models.DateTimeField(blank=True, null=True)), ("created_at", models.DateTimeField(auto_now_add=True)),
            ("category", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="legal_holds", to="data_governance.datacategory")),
            ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="legal_holds_created", to=settings.AUTH_USER_MODEL)),
            ("organization", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="legal_holds", to="accounts.organization")),
            ("released_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="legal_holds_released", to=settings.AUTH_USER_MODEL)),
            ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="legal_holds", to=settings.AUTH_USER_MODEL)),
        ], options={"ordering": ["-created_at"]}),
        migrations.CreateModel(name="DataSubjectRequest", fields=[
            ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
            ("request_type", models.CharField(choices=[("access", "Access"), ("export", "Export"), ("delete", "Delete"), ("correct", "Correct"), ("restrict", "Restrict processing"), ("object", "Object to processing")], max_length=16)),
            ("status", models.CharField(choices=[("received", "Received"), ("verifying", "Verifying identity"), ("approved", "Approved"), ("in_progress", "In progress"), ("completed", "Completed"), ("rejected", "Rejected"), ("blocked_by_hold", "Blocked by legal hold")], default="received", max_length=24)),
            ("verification_notes", models.TextField(blank=True)), ("scope", models.JSONField(blank=True, default=dict)), ("due_at", models.DateTimeField(blank=True, null=True)),
            ("completed_at", models.DateTimeField(blank=True, null=True)), ("rejection_reason", models.TextField(blank=True)), ("evidence_checksum", models.CharField(blank=True, max_length=128)),
            ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ("organization", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="data_subject_requests", to="accounts.organization")),
            ("requested_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="data_subject_requests_opened", to=settings.AUTH_USER_MODEL)),
            ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="data_subject_requests", to=settings.AUTH_USER_MODEL)),
        ], options={"ordering": ["-created_at"]}),
        migrations.CreateModel(name="RetentionJob", fields=[
            ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
            ("status", models.CharField(choices=[("queued", "Queued"), ("running", "Running"), ("completed", "Completed"), ("failed", "Failed"), ("blocked", "Blocked")], default="queued", max_length=16)),
            ("dry_run", models.BooleanField(default=True)), ("cutoff_at", models.DateTimeField()), ("candidate_count", models.PositiveIntegerField(default=0)), ("processed_count", models.PositiveIntegerField(default=0)), ("blocked_count", models.PositiveIntegerField(default=0)),
            ("result_summary", models.JSONField(blank=True, default=dict)), ("error_message", models.TextField(blank=True)), ("started_at", models.DateTimeField(blank=True, null=True)), ("completed_at", models.DateTimeField(blank=True, null=True)), ("created_at", models.DateTimeField(auto_now_add=True)),
            ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="retention_jobs_created", to=settings.AUTH_USER_MODEL)),
            ("policy", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="jobs", to="data_governance.retentionpolicy")),
        ], options={"ordering": ["-created_at"]}),
        migrations.CreateModel(name="AnonymizationRecord", fields=[
            ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
            ("subject_type", models.CharField(max_length=80)), ("subject_id_hash", models.CharField(max_length=128)), ("action", models.CharField(max_length=24)),
            ("fields_changed", models.JSONField(blank=True, default=list)), ("checksum_before", models.CharField(blank=True, max_length=128)), ("checksum_after", models.CharField(blank=True, max_length=128)),
            ("performed_at", models.DateTimeField(default=django.utils.timezone.now)), ("metadata", models.JSONField(blank=True, default=dict)),
            ("asset", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="anonymization_records", to="data_governance.dataasset")),
            ("job", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="anonymization_records", to="data_governance.retentionjob")),
            ("performed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="anonymization_records_performed", to=settings.AUTH_USER_MODEL)),
        ], options={"ordering": ["-performed_at"]}),
        migrations.CreateModel(name="DataInventorySnapshot", fields=[
            ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
            ("asset_count", models.PositiveIntegerField(default=0)), ("pii_asset_count", models.PositiveIntegerField(default=0)), ("restricted_asset_count", models.PositiveIntegerField(default=0)),
            ("active_policy_count", models.PositiveIntegerField(default=0)), ("active_legal_hold_count", models.PositiveIntegerField(default=0)), ("open_subject_request_count", models.PositiveIntegerField(default=0)),
            ("summary", models.JSONField(blank=True, default=dict)), ("generated_at", models.DateTimeField(default=django.utils.timezone.now)),
            ("generated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="data_inventory_snapshots", to=settings.AUTH_USER_MODEL)),
        ], options={"ordering": ["-generated_at"]}),
    ]
