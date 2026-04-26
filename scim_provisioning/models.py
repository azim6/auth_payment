import hashlib
import secrets
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class ScimApplication(models.Model):
    """Tenant-scoped SCIM application/token used by enterprise directories.

    Tokens are only displayed once and are stored as SHA-256 hashes. Use a
    secret manager and rotate tokens regularly in production.
    """

    class Status(models.TextChoices):
        DRAFT = "draft", _("Draft")
        ACTIVE = "active", _("Active")
        SUSPENDED = "suspended", _("Suspended")
        REVOKED = "revoked", _("Revoked")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, related_name="scim_applications")
    name = models.CharField(max_length=180)
    slug = models.SlugField(max_length=80)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    provider = models.CharField(max_length=80, blank=True, help_text="Okta, Azure AD, Google Workspace, OneLogin, custom, etc.")
    token_prefix = models.CharField(max_length=24, blank=True, db_index=True)
    token_hash = models.CharField(max_length=256, blank=True)
    default_role = models.CharField(max_length=16, default="member")
    allow_create_users = models.BooleanField(default=True)
    allow_update_users = models.BooleanField(default=True)
    allow_deactivate_users = models.BooleanField(default=True)
    allow_group_sync = models.BooleanField(default=True)
    require_verified_domain = models.BooleanField(default=True)
    allowed_email_domains = models.JSONField(default=list, blank=True)
    attribute_mapping = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="scim_apps_created")
    last_used_at = models.DateTimeField(null=True, blank=True)
    activated_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("organization", "slug")]
        ordering = ["organization__slug", "name"]
        indexes = [
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["token_prefix"]),
            models.Index(fields=["provider", "status"]),
        ]

    def __str__(self):
        return f"scim:{self.organization.slug}:{self.slug}"

    @staticmethod
    def make_token():
        return "scim_" + secrets.token_urlsafe(40)

    @staticmethod
    def hash_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def rotate_token(self):
        token = self.make_token()
        self.token_prefix = token[:18]
        self.token_hash = self.hash_token(token)
        self.save(update_fields=["token_prefix", "token_hash", "updated_at"])
        return token

    def activate(self):
        self.status = self.Status.ACTIVE
        self.activated_at = timezone.now()
        self.revoked_at = None
        self.save(update_fields=["status", "activated_at", "revoked_at", "updated_at"])

    def revoke(self):
        self.status = self.Status.REVOKED
        self.revoked_at = timezone.now()
        self.save(update_fields=["status", "revoked_at", "updated_at"])

    def mark_used(self):
        self.last_used_at = timezone.now()
        self.save(update_fields=["last_used_at", "updated_at"])


class DirectoryUser(models.Model):
    """External directory user mapped to a local auth user."""

    class Status(models.TextChoices):
        ACTIVE = "active", _("Active")
        SUSPENDED = "suspended", _("Suspended")
        DEPROVISIONED = "deprovisioned", _("Deprovisioned")
        ERROR = "error", _("Error")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, related_name="directory_users")
    scim_application = models.ForeignKey(ScimApplication, on_delete=models.SET_NULL, null=True, blank=True, related_name="directory_users")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="directory_identities")
    external_id = models.CharField(max_length=255)
    user_name = models.EmailField()
    email = models.EmailField()
    display_name = models.CharField(max_length=255, blank=True)
    given_name = models.CharField(max_length=120, blank=True)
    family_name = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.ACTIVE)
    active = models.BooleanField(default=True)
    raw_attributes = models.JSONField(default=dict, blank=True)
    last_synced_at = models.DateTimeField(default=timezone.now)
    deprovisioned_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("organization", "external_id")]
        ordering = ["organization__slug", "email"]
        indexes = [
            models.Index(fields=["organization", "email"]),
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["external_id"]),
            models.Index(fields=["user"]),
        ]

    def __str__(self):
        return f"dir-user:{self.organization.slug}:{self.email}:{self.status}"

    def mark_deprovisioned(self):
        self.active = False
        self.status = self.Status.DEPROVISIONED
        self.deprovisioned_at = timezone.now()
        self.save(update_fields=["active", "status", "deprovisioned_at", "updated_at"])


class DirectoryGroup(models.Model):
    """External directory group mapped to tenant roles or app access."""

    class Status(models.TextChoices):
        ACTIVE = "active", _("Active")
        DISABLED = "disabled", _("Disabled")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, related_name="directory_groups")
    scim_application = models.ForeignKey(ScimApplication, on_delete=models.SET_NULL, null=True, blank=True, related_name="directory_groups")
    external_id = models.CharField(max_length=255)
    display_name = models.CharField(max_length=255)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    mapped_role = models.CharField(max_length=16, blank=True)
    mapped_permissions = models.JSONField(default=list, blank=True)
    raw_attributes = models.JSONField(default=dict, blank=True)
    last_synced_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("organization", "external_id")]
        ordering = ["organization__slug", "display_name"]
        indexes = [
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["external_id"]),
            models.Index(fields=["mapped_role"]),
        ]

    def __str__(self):
        return f"dir-group:{self.organization.slug}:{self.display_name}"


class DirectoryGroupMember(models.Model):
    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, related_name="directory_group_members")
    group = models.ForeignKey(DirectoryGroup, on_delete=models.CASCADE, related_name="members")
    directory_user = models.ForeignKey(DirectoryUser, on_delete=models.CASCADE, related_name="group_memberships")
    external_user_id = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("group", "directory_user")]
        ordering = ["group__display_name", "directory_user__email"]
        indexes = [
            models.Index(fields=["organization", "group"]),
            models.Index(fields=["organization", "directory_user"]),
        ]

    def __str__(self):
        return f"dir-group-member:{self.group_id}:{self.directory_user_id}"


class DeprovisioningPolicy(models.Model):
    """Controls what happens when an external directory disables a user."""

    class Action(models.TextChoices):
        DISABLE_MEMBERSHIP = "disable_membership", _("Disable tenant membership")
        SUSPEND_USER = "suspend_user", _("Suspend local user")
        REVOKE_SESSIONS = "revoke_sessions", _("Revoke sessions and tokens")
        REQUIRE_MANUAL_REVIEW = "manual_review", _("Require manual review")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.OneToOneField("accounts.Organization", on_delete=models.CASCADE, related_name="deprovisioning_policy")
    action = models.CharField(max_length=32, choices=Action.choices, default=Action.DISABLE_MEMBERSHIP)
    grace_period_hours = models.PositiveIntegerField(default=0)
    preserve_billing_owner = models.BooleanField(default=True)
    notify_admins = models.BooleanField(default=True)
    require_approval_for_owners = models.BooleanField(default=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="deprovisioning_policies_updated")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["organization__slug"]

    def __str__(self):
        return f"deprovisioning-policy:{self.organization.slug}:{self.action}"


class ScimSyncJob(models.Model):
    """Directory sync/reconciliation run metadata."""

    class Status(models.TextChoices):
        QUEUED = "queued", _("Queued")
        RUNNING = "running", _("Running")
        COMPLETED = "completed", _("Completed")
        FAILED = "failed", _("Failed")
        CANCELLED = "cancelled", _("Cancelled")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, related_name="scim_sync_jobs")
    scim_application = models.ForeignKey(ScimApplication, on_delete=models.SET_NULL, null=True, blank=True, related_name="sync_jobs")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.QUEUED)
    mode = models.CharField(max_length=32, default="manual")
    dry_run = models.BooleanField(default=True)
    users_seen = models.PositiveIntegerField(default=0)
    users_created = models.PositiveIntegerField(default=0)
    users_updated = models.PositiveIntegerField(default=0)
    users_deprovisioned = models.PositiveIntegerField(default=0)
    groups_seen = models.PositiveIntegerField(default=0)
    groups_updated = models.PositiveIntegerField(default=0)
    errors = models.JSONField(default=list, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="scim_sync_jobs_requested")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["scim_application", "created_at"]),
        ]

    def __str__(self):
        return f"scim-sync:{self.organization.slug}:{self.status}"

    def mark_running(self):
        self.status = self.Status.RUNNING
        self.started_at = timezone.now()
        self.save(update_fields=["status", "started_at"])

    def mark_completed(self):
        self.status = self.Status.COMPLETED
        self.finished_at = timezone.now()
        self.save(update_fields=["status", "finished_at"])


class ScimProvisioningEvent(models.Model):
    """Append-only SCIM provisioning and lifecycle event ledger."""

    class EventType(models.TextChoices):
        TOKEN_ROTATED = "token_rotated", _("Token rotated")
        USER_CREATED = "user_created", _("User created")
        USER_UPDATED = "user_updated", _("User updated")
        USER_DEACTIVATED = "user_deactivated", _("User deactivated")
        GROUP_CREATED = "group_created", _("Group created")
        GROUP_UPDATED = "group_updated", _("Group updated")
        GROUP_MEMBER_SYNCED = "group_member_synced", _("Group member synced")
        SYNC_STARTED = "sync_started", _("Sync started")
        SYNC_COMPLETED = "sync_completed", _("Sync completed")
        ERROR = "error", _("Error")

    class Result(models.TextChoices):
        SUCCESS = "success", _("Success")
        FAILURE = "failure", _("Failure")
        SKIPPED = "skipped", _("Skipped")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey("accounts.Organization", on_delete=models.SET_NULL, null=True, blank=True, related_name="scim_events")
    scim_application = models.ForeignKey(ScimApplication, on_delete=models.SET_NULL, null=True, blank=True, related_name="events")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="scim_events")
    directory_user = models.ForeignKey(DirectoryUser, on_delete=models.SET_NULL, null=True, blank=True, related_name="events")
    directory_group = models.ForeignKey(DirectoryGroup, on_delete=models.SET_NULL, null=True, blank=True, related_name="events")
    event_type = models.CharField(max_length=32, choices=EventType.choices)
    result = models.CharField(max_length=16, choices=Result.choices, default=Result.SUCCESS)
    external_id = models.CharField(max_length=255, blank=True)
    message = models.CharField(max_length=255, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "created_at"]),
            models.Index(fields=["scim_application", "created_at"]),
            models.Index(fields=["event_type", "result"]),
            models.Index(fields=["external_id"]),
        ]

    def __str__(self):
        return f"scim-event:{self.event_type}:{self.result}:{self.created_at:%Y-%m-%d}"
