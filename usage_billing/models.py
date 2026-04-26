import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class Meter(models.Model):
    """Billable usage meter, for example api.calls, storage.gb_hours, or emails.sent."""
    class Aggregation(models.TextChoices):
        SUM = "sum", _("Sum")
        MAX = "max", _("Maximum")
        LAST = "last", _("Last value")
        UNIQUE = "unique", _("Unique count")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.SlugField(max_length=120, unique=True)
    name = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    unit = models.CharField(max_length=40, default="unit")
    aggregation = models.CharField(max_length=16, choices=Aggregation.choices, default=Aggregation.SUM)
    is_active = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["code"]
        indexes = [models.Index(fields=["code"]), models.Index(fields=["is_active"])]

    def __str__(self):
        return self.code


class MeterPrice(models.Model):
    """Rating configuration for a meter under a billing plan or add-on."""
    class PricingModel(models.TextChoices):
        PER_UNIT = "per_unit", _("Per unit")
        TIERED = "tiered", _("Tiered")
        PACKAGE = "package", _("Package")
        FREE_ALLOWANCE = "free_allowance", _("Free allowance")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    meter = models.ForeignKey(Meter, on_delete=models.CASCADE, related_name="prices")
    plan = models.ForeignKey("billing.Plan", on_delete=models.CASCADE, null=True, blank=True, related_name="meter_prices")
    addon = models.ForeignKey("billing.AddOn", on_delete=models.CASCADE, null=True, blank=True, related_name="meter_prices")
    code = models.SlugField(max_length=140, unique=True)
    pricing_model = models.CharField(max_length=32, choices=PricingModel.choices, default=PricingModel.PER_UNIT)
    currency = models.CharField(max_length=3, default="USD")
    unit_amount_cents = models.PositiveIntegerField(default=0)
    free_units = models.DecimalField(max_digits=18, decimal_places=6, default=Decimal("0"))
    tier_config = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["meter__code", "code"]
        indexes = [models.Index(fields=["meter", "is_active"]), models.Index(fields=["plan", "is_active"]), models.Index(fields=["addon", "is_active"])]

    def __str__(self):
        return self.code


class UsageEvent(models.Model):
    """Append-only raw usage event. Idempotency keys prevent duplicate ingestion."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    meter = models.ForeignKey(Meter, on_delete=models.PROTECT, related_name="events")
    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, related_name="usage_events")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="usage_events")
    subscription = models.ForeignKey("billing.Subscription", on_delete=models.SET_NULL, null=True, blank=True, related_name="usage_events")
    quantity = models.DecimalField(max_digits=18, decimal_places=6, default=Decimal("1"))
    occurred_at = models.DateTimeField(default=timezone.now)
    idempotency_key = models.CharField(max_length=180)
    source = models.CharField(max_length=80, default="api")
    attributes = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-occurred_at"]
        constraints = [models.UniqueConstraint(fields=["organization", "meter", "idempotency_key"], name="uniq_usage_event_idempotency")]
        indexes = [models.Index(fields=["organization", "meter", "occurred_at"]), models.Index(fields=["subscription", "meter"]), models.Index(fields=["idempotency_key"])]

    def __str__(self):
        return f"{self.organization_id}:{self.meter.code}:{self.quantity}"


class UsageAggregationWindow(models.Model):
    """Aggregated usage per meter and billing window."""
    class Status(models.TextChoices):
        OPEN = "open", _("Open")
        FINALIZED = "finalized", _("Finalized")
        INVOICED = "invoiced", _("Invoiced")
        VOID = "void", _("Void")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, related_name="usage_windows")
    subscription = models.ForeignKey("billing.Subscription", on_delete=models.CASCADE, related_name="usage_windows")
    meter = models.ForeignKey(Meter, on_delete=models.PROTECT, related_name="windows")
    window_start = models.DateTimeField()
    window_end = models.DateTimeField()
    quantity = models.DecimalField(max_digits=18, decimal_places=6, default=Decimal("0"))
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    finalized_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-window_start"]
        constraints = [models.UniqueConstraint(fields=["subscription", "meter", "window_start", "window_end"], name="uniq_usage_window")]
        indexes = [models.Index(fields=["organization", "status"]), models.Index(fields=["subscription", "status"]), models.Index(fields=["window_start", "window_end"])]

    def finalize(self):
        self.status = self.Status.FINALIZED
        self.finalized_at = timezone.now()
        self.save(update_fields=["status", "finalized_at", "updated_at"])


class RatedUsageLine(models.Model):
    """Rated usage line ready to be pushed to invoices or provider usage records."""
    class Status(models.TextChoices):
        DRAFT = "draft", _("Draft")
        READY = "ready", _("Ready")
        INVOICED = "invoiced", _("Invoiced")
        FAILED = "failed", _("Failed")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    window = models.OneToOneField(UsageAggregationWindow, on_delete=models.CASCADE, related_name="rated_line")
    meter_price = models.ForeignKey(MeterPrice, on_delete=models.PROTECT, related_name="rated_lines")
    quantity = models.DecimalField(max_digits=18, decimal_places=6)
    free_units_applied = models.DecimalField(max_digits=18, decimal_places=6, default=Decimal("0"))
    billable_quantity = models.DecimalField(max_digits=18, decimal_places=6, default=Decimal("0"))
    currency = models.CharField(max_length=3, default="USD")
    amount_cents = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    invoice = models.ForeignKey("billing.Invoice", on_delete=models.SET_NULL, null=True, blank=True, related_name="usage_lines")
    rating_details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status"]), models.Index(fields=["currency", "amount_cents"])]

    def __str__(self):
        return f"rated:{self.window_id}:{self.amount_cents}{self.currency}"


class CreditGrant(models.Model):
    """Prepaid/manual credits that can offset usage charges."""
    class Status(models.TextChoices):
        ACTIVE = "active", _("Active")
        EXPIRED = "expired", _("Expired")
        DEPLETED = "depleted", _("Depleted")
        VOID = "void", _("Void")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, related_name="credit_grants")
    currency = models.CharField(max_length=3, default="USD")
    original_amount_cents = models.PositiveIntegerField()
    remaining_amount_cents = models.PositiveIntegerField()
    reason = models.CharField(max_length=140, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="credit_grants_created")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["organization", "status"]), models.Index(fields=["expires_at"])]

    def __str__(self):
        return f"credit:{self.organization_id}:{self.remaining_amount_cents}{self.currency}"


class CreditApplication(models.Model):
    """Ledger entry showing credit consumption against a rated usage line."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    credit_grant = models.ForeignKey(CreditGrant, on_delete=models.PROTECT, related_name="applications")
    rated_line = models.ForeignKey(RatedUsageLine, on_delete=models.CASCADE, related_name="credit_applications")
    amount_cents = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["credit_grant"]), models.Index(fields=["rated_line"])]


class UsageReconciliationRun(models.Model):
    """Operational record for comparing local metered usage with provider/provider-invoice usage."""
    class Status(models.TextChoices):
        PLANNED = "planned", _("Planned")
        RUNNING = "running", _("Running")
        COMPLETED = "completed", _("Completed")
        FAILED = "failed", _("Failed")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.CharField(max_length=40, default="stripe")
    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, null=True, blank=True, related_name="usage_reconciliation_runs")
    window_start = models.DateTimeField()
    window_end = models.DateTimeField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PLANNED)
    local_total_cents = models.IntegerField(default=0)
    provider_total_cents = models.IntegerField(default=0)
    mismatch_count = models.PositiveIntegerField(default=0)
    report = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="usage_reconciliations_created")
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["provider", "status"]), models.Index(fields=["window_start", "window_end"])]
