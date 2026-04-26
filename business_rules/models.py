import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class ProductAccessOverride(models.Model):
    """Admin-created override for one user or organization and one product/action.

    Overrides are used for real business operations such as granting free access,
    blocking only chat, increasing a ZATCA document limit for one customer, or
    temporarily allowing blog writing while a payment issue is resolved.
    """

    class Effect(models.TextChoices):
        ALLOW = "allow", _("Allow")
        DENY = "deny", _("Deny")
        LIMIT = "limit", _("Override limit")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name="business_access_overrides")
    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, null=True, blank=True, related_name="business_access_overrides")
    product = models.SlugField(max_length=80)
    action = models.SlugField(max_length=80, blank=True, help_text="Blank means product-wide override.")
    entitlement_key = models.CharField(max_length=140, blank=True, help_text="Optional entitlement key affected by this override.")
    effect = models.CharField(max_length=16, choices=Effect.choices)
    bool_value = models.BooleanField(null=True, blank=True)
    int_value = models.IntegerField(null=True, blank=True)
    reason = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="business_access_overrides_created")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "product", "action", "is_active"]),
            models.Index(fields=["organization", "product", "action", "is_active"]),
            models.Index(fields=["product", "action"]),
            models.Index(fields=["expires_at"]),
        ]

    def __str__(self):
        subject = self.organization_id or self.user_id
        suffix = f".{self.action}" if self.action else ".*"
        return f"override:{subject}:{self.product}{suffix}:{self.effect}"

    @property
    def is_effective(self) -> bool:
        return self.is_active and (self.expires_at is None or timezone.now() < self.expires_at)

    @property
    def value(self):
        if self.effect == self.Effect.LIMIT:
            return self.int_value
        if self.bool_value is not None:
            return self.bool_value
        return self.effect == self.Effect.ALLOW


class ProductUsageEvent(models.Model):
    """Append-only product usage event for enforcing limits and debugging access checks."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name="business_usage_events")
    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, null=True, blank=True, related_name="business_usage_events")
    product = models.SlugField(max_length=80)
    action = models.SlugField(max_length=80)
    quantity = models.PositiveIntegerField(default=1)
    period_key = models.CharField(max_length=32, blank=True, help_text="YYYY-MM, YYYY-MM-DD, or total depending on action rule.")
    idempotency_key = models.CharField(max_length=180, blank=True)
    source = models.CharField(max_length=80, default="api")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "product", "action", "period_key"]),
            models.Index(fields=["organization", "product", "action", "period_key"]),
            models.Index(fields=["product", "action", "created_at"]),
            models.Index(fields=["idempotency_key"]),
        ]
        constraints = [
            models.UniqueConstraint(fields=["idempotency_key"], condition=models.Q(idempotency_key__gt=""), name="uniq_business_usage_idempotency_key"),
        ]

    def __str__(self):
        subject = self.organization_id or self.user_id
        return f"usage:{subject}:{self.product}.{self.action}:{self.quantity}"


class ProductAccessDecision(models.Model):
    """Audit record of access decisions made for product apps."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="business_access_decisions")
    organization = models.ForeignKey("accounts.Organization", on_delete=models.SET_NULL, null=True, blank=True, related_name="business_access_decisions")
    product = models.SlugField(max_length=80)
    action = models.SlugField(max_length=80)
    allowed = models.BooleanField(default=False)
    reason = models.CharField(max_length=120)
    remaining = models.IntegerField(null=True, blank=True)
    limit = models.IntegerField(null=True, blank=True)
    used = models.IntegerField(null=True, blank=True)
    plan_codes = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["product", "action", "allowed", "created_at"]),
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["organization", "created_at"]),
        ]

    def __str__(self):
        return f"decision:{self.product}.{self.action}:{self.allowed}:{self.reason}"
