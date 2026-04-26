# Generated manually for v18 operations maturity.

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="EnvironmentCheck",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("key", models.CharField(max_length=160, unique=True)),
                ("status", models.CharField(choices=[("pass", "Pass"), ("warn", "Warn"), ("fail", "Fail")], default="warn", max_length=16)),
                ("message", models.TextField(blank=True)),
                ("details", models.JSONField(blank=True, default=dict)),
                ("checked_at", models.DateTimeField(default=django.utils.timezone.now)),
            ],
            options={"ordering": ["key"]},
        ),
        migrations.CreateModel(
            name="ServiceHealthCheck",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120, unique=True)),
                ("status", models.CharField(choices=[("healthy", "Healthy"), ("degraded", "Degraded"), ("down", "Down"), ("unknown", "Unknown")], default="unknown", max_length=16)),
                ("latency_ms", models.PositiveIntegerField(default=0)),
                ("message", models.TextField(blank=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("checked_at", models.DateTimeField(default=django.utils.timezone.now)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="BackupSnapshot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("label", models.CharField(max_length=180)),
                ("status", models.CharField(choices=[("requested", "Requested"), ("running", "Running"), ("succeeded", "Succeeded"), ("failed", "Failed"), ("restored", "Restored")], default="requested", max_length=24)),
                ("database_name", models.CharField(default="default", max_length=120)),
                ("storage_uri", models.CharField(blank=True, max_length=500)),
                ("checksum_sha256", models.CharField(blank=True, max_length=64)),
                ("size_bytes", models.PositiveBigIntegerField(default=0)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("error_message", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("requested_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="backup_snapshots_requested", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="MaintenanceWindow",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=180)),
                ("status", models.CharField(choices=[("scheduled", "Scheduled"), ("active", "Active"), ("completed", "Completed"), ("cancelled", "Cancelled")], default="scheduled", max_length=24)),
                ("starts_at", models.DateTimeField()),
                ("ends_at", models.DateTimeField()),
                ("affected_services", models.JSONField(blank=True, default=list)),
                ("customer_message", models.TextField(blank=True)),
                ("internal_notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="maintenance_windows_created", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-starts_at"]},
        ),
        migrations.CreateModel(
            name="ReleaseRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("version", models.CharField(max_length=40, unique=True)),
                ("status", models.CharField(choices=[("planned", "Planned"), ("staged", "Staged"), ("released", "Released"), ("rolled_back", "Rolled back"), ("failed", "Failed")], default="planned", max_length=24)),
                ("git_sha", models.CharField(blank=True, max_length=80)),
                ("image_tag", models.CharField(blank=True, max_length=160)),
                ("changelog", models.TextField(blank=True)),
                ("deployed_at", models.DateTimeField(blank=True, null=True)),
                ("rollback_notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("deployed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="releases_deployed", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="StatusIncident",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=180)),
                ("state", models.CharField(choices=[("investigating", "Investigating"), ("identified", "Identified"), ("monitoring", "Monitoring"), ("resolved", "Resolved")], default="investigating", max_length=24)),
                ("impact", models.CharField(choices=[("none", "None"), ("minor", "Minor"), ("major", "Major"), ("critical", "Critical")], default="minor", max_length=16)),
                ("affected_services", models.JSONField(blank=True, default=list)),
                ("public_message", models.TextField(blank=True)),
                ("internal_notes", models.TextField(blank=True)),
                ("started_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("resolved_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="status_incidents_created", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-started_at"]},
        ),
        migrations.CreateModel(
            name="RestoreRun",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("planned", "Planned"), ("approved", "Approved"), ("running", "Running"), ("succeeded", "Succeeded"), ("failed", "Failed"), ("cancelled", "Cancelled")], default="planned", max_length=24)),
                ("target_environment", models.CharField(default="staging", max_length=80)),
                ("reason", models.TextField()),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("result_notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("approved_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="restore_runs_approved", to=settings.AUTH_USER_MODEL)),
                ("backup", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="restore_runs", to="ops.backupsnapshot")),
                ("requested_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="restore_runs_requested", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
