import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class DashboardWidget(models.Model):
    """Configurable staff dashboard widget for auth, billing, ops, and risk domains."""

    class WidgetType(models.TextChoices):
        METRIC = "metric", _("Metric")
        TABLE = "table", _("Table")
        QUEUE = "queue", _("Queue")
        LINK = "link", _("Link")
        CHART = "chart", _("Chart")

    class Domain(models.TextChoices):
        AUTH = "auth", _("Auth")
        BILLING = "billing", _("Billing")
        SECURITY = "security", _("Security")
        COMPLIANCE = "compliance", _("Compliance")
        OPS = "ops", _("Operations")
        PLATFORM = "platform", _("Developer Platform")
        NOTIFICATIONS = "notifications", _("Notifications")
        OBSERVABILITY = "observability", _("Observability")
        FRAUD = "fraud", _("Fraud/Abuse")
        CUSTOM = "custom", _("Custom")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    key = models.SlugField(max_length=120, unique=True)
    title = models.CharField(max_length=160)
    domain = models.CharField(max_length=32, choices=Domain.choices)
    widget_type = models.CharField(max_length=16, choices=WidgetType.choices, default=WidgetType.METRIC)
    description = models.TextField(blank=True)
    query_config = models.JSONField(default=dict, blank=True, help_text="Declarative backend query/card configuration. Never store secrets here.")
    display_config = models.JSONField(default=dict, blank=True)
    permission_code = models.CharField(max_length=120, blank=True, help_text="Optional RBAC permission required to see this widget.")
    enabled = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=100)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="created_dashboard_widgets")
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="updated_dashboard_widgets")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "domain", "title"]
        indexes = [models.Index(fields=["domain", "enabled"]), models.Index(fields=["permission_code"])]

    def __str__(self):
        return f"{self.domain}:{self.key}"


class SavedAdminView(models.Model):
    """Saved list filters/search/sort state for repeatable operator workflows."""

    class Visibility(models.TextChoices):
        PRIVATE = "private", _("Private")
        TEAM = "team", _("Team")
        GLOBAL = "global", _("Global")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=160)
    resource = models.CharField(max_length=120, help_text="Example: users, organizations, billing.subscriptions, fraud.cases")
    visibility = models.CharField(max_length=16, choices=Visibility.choices, default=Visibility.PRIVATE)
    filters = models.JSONField(default=dict, blank=True)
    columns = models.JSONField(default=list, blank=True)
    sort = models.JSONField(default=list, blank=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_admin_views")
    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, null=True, blank=True, related_name="saved_admin_views")
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["resource", "name"]
        indexes = [models.Index(fields=["resource", "visibility"]), models.Index(fields=["owner", "resource"])]
        constraints = [
            models.UniqueConstraint(fields=["owner", "resource", "name"], name="unique_admin_view_per_owner_resource_name"),
        ]

    def __str__(self):
        return f"{self.resource}:{self.name}"


class OperatorTask(models.Model):
    """Internal task assigned to support, billing, security, or compliance operators."""

    class Status(models.TextChoices):
        OPEN = "open", _("Open")
        IN_PROGRESS = "in_progress", _("In progress")
        BLOCKED = "blocked", _("Blocked")
        DONE = "done", _("Done")
        CANCELED = "canceled", _("Canceled")

    class Priority(models.TextChoices):
        LOW = "low", _("Low")
        NORMAL = "normal", _("Normal")
        HIGH = "high", _("High")
        URGENT = "urgent", _("Urgent")

    class Domain(models.TextChoices):
        SUPPORT = "support", _("Support")
        AUTH = "auth", _("Auth")
        BILLING = "billing", _("Billing")
        SECURITY = "security", _("Security")
        COMPLIANCE = "compliance", _("Compliance")
        OPS = "ops", _("Operations")
        FRAUD = "fraud", _("Fraud/Abuse")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    domain = models.CharField(max_length=24, choices=Domain.choices, default=Domain.SUPPORT)
    priority = models.CharField(max_length=16, choices=Priority.choices, default=Priority.NORMAL)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.OPEN)
    description = models.TextField(blank=True)
    target_type = models.CharField(max_length=80, blank=True)
    target_id = models.CharField(max_length=128, blank=True)
    target_url = models.CharField(max_length=500, blank=True)
    organization = models.ForeignKey("accounts.Organization", on_delete=models.SET_NULL, null=True, blank=True, related_name="operator_tasks")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="created_operator_tasks")
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_operator_tasks")
    due_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["status", "-priority", "due_at", "-created_at"]
        indexes = [models.Index(fields=["status", "priority"]), models.Index(fields=["assigned_to", "status"]), models.Index(fields=["domain", "status"]), models.Index(fields=["organization", "status"])]

    def mark_started(self, user=None):
        self.status = self.Status.IN_PROGRESS
        self.started_at = self.started_at or timezone.now()
        if user and not self.assigned_to:
            self.assigned_to = user
        self.save(update_fields=["status", "started_at", "assigned_to", "updated_at"])

    def mark_done(self):
        self.status = self.Status.DONE
        self.completed_at = timezone.now()
        self.save(update_fields=["status", "completed_at", "updated_at"])

    def __str__(self):
        return self.title


class BulkActionRequest(models.Model):
    """Two-step bulk action request for high-risk admin changes."""

    class Action(models.TextChoices):
        EXPORT_USERS = "export_users", _("Export users")
        DISABLE_USERS = "disable_users", _("Disable users")
        REVOKE_SESSIONS = "revoke_sessions", _("Revoke sessions")
        UPDATE_ORG_LIMITS = "update_org_limits", _("Update organization limits")
        APPLY_BILLING_OVERRIDE = "apply_billing_override", _("Apply billing override")
        RECALCULATE_ENTITLEMENTS = "recalculate_entitlements", _("Recalculate entitlements")
        SEND_NOTIFICATION = "send_notification", _("Send notification")
        CUSTOM = "custom", _("Custom")

    class Status(models.TextChoices):
        DRAFT = "draft", _("Draft")
        PENDING_APPROVAL = "pending_approval", _("Pending approval")
        APPROVED = "approved", _("Approved")
        REJECTED = "rejected", _("Rejected")
        RUNNING = "running", _("Running")
        COMPLETED = "completed", _("Completed")
        FAILED = "failed", _("Failed")
        CANCELED = "canceled", _("Canceled")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    action = models.CharField(max_length=40, choices=Action.choices)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.DRAFT)
    reason = models.TextField()
    target_filter = models.JSONField(default=dict, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    estimated_count = models.PositiveIntegerField(default=0)
    processed_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="requested_bulk_actions")
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="approved_bulk_actions")
    approved_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_summary = models.TextField(blank=True)
    idempotency_key = models.CharField(max_length=160, blank=True, unique=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["action", "status"]), models.Index(fields=["requested_by", "status"]), models.Index(fields=["idempotency_key"])]

    def submit(self):
        if self.status == self.Status.DRAFT:
            self.status = self.Status.PENDING_APPROVAL
            self.save(update_fields=["status", "updated_at"])

    def approve(self, user):
        if self.requested_by_id and user and self.requested_by_id == user.id:
            raise ValueError("Bulk action requests require a different approver.")
        self.status = self.Status.APPROVED
        self.approved_by = user
        self.approved_at = timezone.now()
        self.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])

    def __str__(self):
        return f"{self.action}:{self.status}"


class AdminNote(models.Model):
    """Operator note linked to a user, organization, or external platform object."""

    class Visibility(models.TextChoices):
        STAFF = "staff", _("Staff")
        SECURITY = "security", _("Security only")
        BILLING = "billing", _("Billing only")
        COMPLIANCE = "compliance", _("Compliance only")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subject_type = models.CharField(max_length=80)
    subject_id = models.CharField(max_length=128)
    title = models.CharField(max_length=200)
    body = models.TextField()
    visibility = models.CharField(max_length=24, choices=Visibility.choices, default=Visibility.STAFF)
    pinned = models.BooleanField(default=False)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="admin_notes")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-pinned", "-created_at"]
        indexes = [models.Index(fields=["subject_type", "subject_id"]), models.Index(fields=["visibility", "pinned"])]

    def __str__(self):
        return f"{self.subject_type}:{self.subject_id}:{self.title}"


class AdminWorkspacePreference(models.Model):
    """Per-operator console preferences without mixing UI state into user/account models."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="admin_console_preferences")
    landing_page = models.CharField(max_length=120, default="overview")
    timezone_name = models.CharField(max_length=80, default="UTC")
    favorite_resources = models.JSONField(default=list, blank=True)
    dismissed_banners = models.JSONField(default=list, blank=True)
    dashboard_layout = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["user__email"]

    def __str__(self):
        return f"preferences:{self.user_id}"


class DashboardSnapshot(models.Model):
    """Precomputed summary for fast admin-console loading and auditability."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120, default="global")
    generated_at = models.DateTimeField(default=timezone.now)
    generated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="generated_dashboard_snapshots")
    payload = models.JSONField(default=dict, blank=True)
    source_counts = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-generated_at"]
        indexes = [models.Index(fields=["name", "generated_at"])]

    def __str__(self):
        return f"{self.name}:{self.generated_at.isoformat()}"
