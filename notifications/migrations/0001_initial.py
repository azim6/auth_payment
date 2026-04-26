# Generated for django-auth-platform v20 notification infrastructure.
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("accounts", "0009_rbac_policies"),
        ("billing", "0006_reliability_ops"),
    ]

    operations = [
        migrations.CreateModel(
            name="NotificationProvider",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=120)),
                ("channel", models.CharField(choices=[("email", "Email"), ("sms", "SMS"), ("push", "Push"), ("in_app", "In-app"), ("webhook", "Webhook")], max_length=16)),
                ("provider_code", models.CharField(help_text="ses, sendgrid, twilio, fcm, apns, internal, etc.", max_length=80)),
                ("status", models.CharField(choices=[("active", "Active"), ("disabled", "Disabled"), ("degraded", "Degraded")], default="active", max_length=16)),
                ("priority", models.PositiveSmallIntegerField(default=100)),
                ("config", models.JSONField(blank=True, default=dict, help_text="Non-secret provider metadata only.")),
                ("last_success_at", models.DateTimeField(blank=True, null=True)),
                ("last_failure_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["channel", "priority", "name"]},
        ),
        migrations.CreateModel(
            name="NotificationTemplate",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("key", models.SlugField(max_length=120)),
                ("channel", models.CharField(choices=[("email", "Email"), ("sms", "SMS"), ("push", "Push"), ("in_app", "In-app"), ("webhook", "Webhook")], max_length=16)),
                ("locale", models.CharField(default="en", max_length=16)),
                ("version", models.PositiveIntegerField(default=1)),
                ("is_active", models.BooleanField(default=True)),
                ("subject_template", models.CharField(blank=True, max_length=240)),
                ("body_template", models.TextField()),
                ("html_template", models.TextField(blank=True)),
                ("variables_schema", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="notification_templates_created", to=settings.AUTH_USER_MODEL)),
                ("organization", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="notification_templates", to="accounts.organization")),
                ("project", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="notification_templates", to="billing.project")),
            ],
            options={"ordering": ["key", "channel", "locale", "-version"], "unique_together": {("key", "channel", "locale", "version", "organization")}},
        ),
        migrations.CreateModel(
            name="NotificationPreference",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("topic", models.CharField(help_text="security, billing, product, marketing, compliance, etc.", max_length=120)),
                ("channel", models.CharField(choices=[("email", "Email"), ("sms", "SMS"), ("push", "Push"), ("in_app", "In-app"), ("webhook", "Webhook")], max_length=16)),
                ("enabled", models.BooleanField(default=True)),
                ("locale", models.CharField(default="en", max_length=16)),
                ("timezone", models.CharField(default="UTC", max_length=64)),
                ("quiet_hours_start", models.TimeField(blank=True, null=True)),
                ("quiet_hours_end", models.TimeField(blank=True, null=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("organization", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="notification_preferences", to="accounts.organization")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="notification_preferences", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["user", "organization", "topic", "channel"], "unique_together": {("user", "organization", "topic", "channel")}},
        ),
        migrations.CreateModel(
            name="DevicePushToken",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("platform", models.CharField(choices=[("android", "Android"), ("windows", "Windows"), ("web", "Web")], max_length=16)),
                ("device_id", models.CharField(blank=True, max_length=160)),
                ("token_prefix", models.CharField(max_length=24)),
                ("token_hash", models.CharField(max_length=128, unique=True)),
                ("is_active", models.BooleanField(default=True)),
                ("last_used_at", models.DateTimeField(blank=True, null=True)),
                ("revoked_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("organization", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="push_tokens", to="accounts.organization")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="push_tokens", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="NotificationEvent",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("event_type", models.CharField(max_length=120)),
                ("topic", models.CharField(default="product", max_length=120)),
                ("priority", models.CharField(choices=[("low", "Low"), ("normal", "Normal"), ("high", "High"), ("critical", "Critical")], default="normal", max_length=16)),
                ("status", models.CharField(choices=[("received", "Received"), ("queued", "Queued"), ("dispatched", "Dispatched"), ("skipped", "Skipped"), ("failed", "Failed")], default="received", max_length=16)),
                ("idempotency_key", models.CharField(blank=True, max_length=160)),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("scheduled_for", models.DateTimeField(default=django.utils.timezone.now)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="notification_events_created", to=settings.AUTH_USER_MODEL)),
                ("organization", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="notification_events", to="accounts.organization")),
                ("project", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="notification_events", to="billing.project")),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="notification_events", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="NotificationDelivery",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("channel", models.CharField(choices=[("email", "Email"), ("sms", "SMS"), ("push", "Push"), ("in_app", "In-app"), ("webhook", "Webhook")], max_length=16)),
                ("recipient", models.CharField(max_length=320)),
                ("recipient_hash", models.CharField(db_index=True, max_length=128)),
                ("subject", models.CharField(blank=True, max_length=240)),
                ("body", models.TextField(blank=True)),
                ("html_body", models.TextField(blank=True)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("sent", "Sent"), ("skipped", "Skipped"), ("failed", "Failed"), ("dead", "Dead-lettered")], default="pending", max_length=16)),
                ("attempt_count", models.PositiveIntegerField(default=0)),
                ("max_attempts", models.PositiveIntegerField(default=5)),
                ("next_attempt_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("last_attempt_at", models.DateTimeField(blank=True, null=True)),
                ("sent_at", models.DateTimeField(blank=True, null=True)),
                ("provider_message_id", models.CharField(blank=True, max_length=160)),
                ("error_message", models.TextField(blank=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("event", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="deliveries", to="notifications.notificationevent")),
                ("provider", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="deliveries", to="notifications.notificationprovider")),
                ("template", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="deliveries", to="notifications.notificationtemplate")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="NotificationSuppression",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("channel", models.CharField(choices=[("email", "Email"), ("sms", "SMS"), ("push", "Push"), ("in_app", "In-app"), ("webhook", "Webhook")], max_length=16)),
                ("recipient_hash", models.CharField(max_length=128)),
                ("reason", models.CharField(choices=[("unsubscribe", "Unsubscribe"), ("bounce", "Hard bounce"), ("complaint", "Complaint"), ("admin_block", "Admin block")], max_length=24)),
                ("note", models.TextField(blank=True)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="notification_suppressions_created", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"], "unique_together": {("channel", "recipient_hash", "reason")}},
        ),
        migrations.AddConstraint(model_name="notificationevent", constraint=models.UniqueConstraint(condition=models.Q(("idempotency_key", ""), _negated=True), fields=("idempotency_key",), name="uniq_notification_idempotency_key")),
    ]
