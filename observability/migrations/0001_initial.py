# Generated for django-auth-platform v21 observability infrastructure.
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import uuid


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL), ("accounts", "0009_rbac_policies")]
    operations = [
        migrations.CreateModel(name="ApplicationEvent", fields=[
            ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
            ("event_type", models.CharField(max_length=160)), ("source_app", models.CharField(default="auth-platform", max_length=80)),
            ("severity", models.CharField(default="info", max_length=16)), ("request_id", models.CharField(blank=True, db_index=True, max_length=120)),
            ("trace_id", models.CharField(blank=True, db_index=True, max_length=120)), ("span_id", models.CharField(blank=True, max_length=120)),
            ("subject_type", models.CharField(blank=True, max_length=80)), ("subject_id", models.CharField(blank=True, max_length=160)),
            ("message", models.TextField(blank=True)), ("payload", models.JSONField(blank=True, default=dict)),
            ("occurred_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)), ("created_at", models.DateTimeField(auto_now_add=True)),
            ("organization", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="application_events", to="accounts.organization")),
            ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="application_events", to=settings.AUTH_USER_MODEL)),
        ], options={"ordering": ["-occurred_at"]}),
        migrations.CreateModel(name="MetricSnapshot", fields=[
            ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
            ("name", models.CharField(max_length=160)), ("kind", models.CharField(default="gauge", max_length=16)),
            ("source_app", models.CharField(default="auth-platform", max_length=80)), ("value", models.DecimalField(decimal_places=6, max_digits=20)),
            ("unit", models.CharField(blank=True, max_length=32)), ("dimensions", models.JSONField(blank=True, default=dict)),
            ("bucket_start", models.DateTimeField(db_index=True, default=django.utils.timezone.now)), ("bucket_seconds", models.PositiveIntegerField(default=60)),
            ("created_at", models.DateTimeField(auto_now_add=True)),
        ], options={"ordering": ["-bucket_start", "name"], "unique_together": {("name", "source_app", "bucket_start", "bucket_seconds")}}),
        migrations.CreateModel(name="TraceSample", fields=[
            ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
            ("trace_id", models.CharField(db_index=True, max_length=120)), ("request_id", models.CharField(blank=True, db_index=True, max_length=120)),
            ("method", models.CharField(blank=True, max_length=12)), ("path", models.CharField(max_length=500)),
            ("status_code", models.PositiveIntegerField(default=0)), ("duration_ms", models.PositiveIntegerField(default=0)), ("status", models.CharField(default="ok", max_length=16)),
            ("source_app", models.CharField(default="auth-platform", max_length=80)), ("metadata", models.JSONField(blank=True, default=dict)),
            ("started_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)), ("created_at", models.DateTimeField(auto_now_add=True)),
            ("organization", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="trace_samples", to="accounts.organization")),
            ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="trace_samples", to=settings.AUTH_USER_MODEL)),
        ], options={"ordering": ["-started_at"]}),
        migrations.CreateModel(name="ServiceLevelObjective", fields=[
            ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
            ("name", models.CharField(max_length=160, unique=True)), ("source_app", models.CharField(default="auth-platform", max_length=80)),
            ("target_percentage", models.DecimalField(decimal_places=3, default=99.9, max_digits=6)), ("window", models.CharField(default="30d", max_length=8)),
            ("good_events_query", models.JSONField(blank=True, default=dict)), ("total_events_query", models.JSONField(blank=True, default=dict)),
            ("is_active", models.BooleanField(default=True)), ("owner_team", models.CharField(blank=True, max_length=120)), ("runbook_url", models.CharField(blank=True, max_length=500)),
            ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
        ], options={"ordering": ["name"]}),
        migrations.CreateModel(name="SLOSnapshot", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("measured_percentage", models.DecimalField(decimal_places=4, max_digits=7)), ("good_events", models.PositiveBigIntegerField(default=0)),
            ("total_events", models.PositiveBigIntegerField(default=0)), ("error_budget_remaining", models.DecimalField(decimal_places=4, default=100, max_digits=7)),
            ("window_start", models.DateTimeField()), ("window_end", models.DateTimeField(default=django.utils.timezone.now)), ("notes", models.TextField(blank=True)), ("created_at", models.DateTimeField(auto_now_add=True)),
            ("slo", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="snapshots", to="observability.servicelevelobjective")),
        ], options={"ordering": ["-window_end"]}),
        migrations.CreateModel(name="AlertRule", fields=[
            ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)), ("name", models.CharField(max_length=160, unique=True)),
            ("metric_name", models.CharField(max_length=160)), ("comparator", models.CharField(default="gte", max_length=8)), ("threshold", models.DecimalField(decimal_places=6, max_digits=20)),
            ("severity", models.CharField(default="error", max_length=16)), ("status", models.CharField(default="active", max_length=16)), ("evaluation_window_seconds", models.PositiveIntegerField(default=300)),
            ("notify_channels", models.JSONField(blank=True, default=list)), ("metadata", models.JSONField(blank=True, default=dict)), ("last_triggered_at", models.DateTimeField(blank=True, null=True)),
            ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="alert_rules_created", to=settings.AUTH_USER_MODEL)),
        ], options={"ordering": ["name"]}),
        migrations.CreateModel(name="AlertIncident", fields=[
            ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)), ("state", models.CharField(default="open", max_length=24)),
            ("severity", models.CharField(default="error", max_length=16)), ("title", models.CharField(max_length=240)), ("description", models.TextField(blank=True)),
            ("triggered_value", models.DecimalField(blank=True, decimal_places=6, max_digits=20, null=True)), ("payload", models.JSONField(blank=True, default=dict)),
            ("opened_at", models.DateTimeField(default=django.utils.timezone.now)), ("acknowledged_at", models.DateTimeField(blank=True, null=True)), ("resolved_at", models.DateTimeField(blank=True, null=True)),
            ("acknowledged_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="alert_incidents_acknowledged", to=settings.AUTH_USER_MODEL)),
            ("resolved_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="alert_incidents_resolved", to=settings.AUTH_USER_MODEL)),
            ("rule", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="incidents", to="observability.alertrule")),
        ], options={"ordering": ["-opened_at"]}),
    ]
