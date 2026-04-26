import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class Project(models.Model):
    """Billable product/project such as blog, store, social, or API."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.SlugField(max_length=80, unique=True)
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["code"]
        indexes = [models.Index(fields=["code"]), models.Index(fields=["is_active"])]

    def __str__(self):
        return self.code


class Plan(models.Model):
    """Admin-managed plan that can be global or project-specific."""
    class Visibility(models.TextChoices):
        PUBLIC = "public", _("Public")
        PRIVATE = "private", _("Private/admin assigned")
        INTERNAL = "internal", _("Internal")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.PROTECT, null=True, blank=True, related_name="plans")
    code = models.SlugField(max_length=100, unique=True)
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    visibility = models.CharField(max_length=16, choices=Visibility.choices, default=Visibility.PUBLIC)
    is_active = models.BooleanField(default=True)
    trial_days = models.PositiveIntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="billing_plans_created")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["project__code", "code"]
        indexes = [models.Index(fields=["code"]), models.Index(fields=["project", "is_active"]), models.Index(fields=["visibility", "is_active"])]

    def __str__(self):
        return self.code


class Price(models.Model):
    """Recurring or one-time price. Custom/manual prices are created by admins."""
    class Interval(models.TextChoices):
        MONTH = "month", _("Monthly")
        YEAR = "year", _("Yearly")
        ONE_TIME = "one_time", _("One time")
        CUSTOM = "custom", _("Custom/manual")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name="prices")
    code = models.SlugField(max_length=120, unique=True)
    currency = models.CharField(max_length=3, default="USD")
    amount_cents = models.PositiveIntegerField(default=0)
    interval = models.CharField(max_length=16, choices=Interval.choices, default=Interval.MONTH)
    is_active = models.BooleanField(default=True)
    is_custom = models.BooleanField(default=False)
    provider_price_id = models.CharField(max_length=180, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="billing_prices_created")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["plan", "amount_cents"]
        indexes = [models.Index(fields=["plan", "is_active"]), models.Index(fields=["currency", "amount_cents"]), models.Index(fields=["provider_price_id"])]

    def __str__(self):
        return f"{self.code}:{self.amount_cents}{self.currency}"


class BillingCustomer(models.Model):
    """Billing profile linked to an organization tenant or individual user."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.OneToOneField("accounts.Organization", on_delete=models.CASCADE, null=True, blank=True, related_name="billing_customer")
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name="billing_customer")
    billing_email = models.EmailField(blank=True)
    billing_name = models.CharField(max_length=180, blank=True)
    provider = models.CharField(max_length=40, default="manual")
    provider_customer_id = models.CharField(max_length=180, blank=True)
    tax_id = models.CharField(max_length=80, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["provider", "provider_customer_id"]), models.Index(fields=["billing_email"])]

    def __str__(self):
        subject = self.organization_id or self.user_id
        return f"billing-customer:{subject}"

    def clean(self):
        from django.core.exceptions import ValidationError
        if bool(self.organization_id) == bool(self.user_id):
            raise ValidationError("Exactly one of organization or user must be set.")


class Subscription(models.Model):
    """Tenant/user subscription controlled by provider webhooks or admins."""
    class Status(models.TextChoices):
        TRIALING = "trialing", _("Trialing")
        ACTIVE = "active", _("Active")
        PAST_DUE = "past_due", _("Past due")
        PAUSED = "paused", _("Paused")
        CANCELLED = "cancelled", _("Cancelled")
        EXPIRED = "expired", _("Expired")
        FREE = "free", _("Free/manual")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(BillingCustomer, on_delete=models.CASCADE, related_name="subscriptions")
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="subscriptions")
    price = models.ForeignKey(Price, on_delete=models.PROTECT, null=True, blank=True, related_name="subscriptions")
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.ACTIVE)
    quantity = models.PositiveIntegerField(default=1)
    seat_limit = models.PositiveIntegerField(default=1)
    trial_ends_at = models.DateTimeField(null=True, blank=True)
    grace_period_ends_at = models.DateTimeField(null=True, blank=True)
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    cancel_at_period_end = models.BooleanField(default=False)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    provider = models.CharField(max_length=40, default="manual")
    provider_subscription_id = models.CharField(max_length=180, blank=True)
    admin_note = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="billing_subscriptions_created")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["customer", "status"]), models.Index(fields=["plan", "status"]), models.Index(fields=["provider", "provider_subscription_id"]), models.Index(fields=["current_period_end"])]

    def __str__(self):
        return f"subscription:{self.customer_id}:{self.plan.code}:{self.status}"

    @property
    def is_entitled(self):
        now = timezone.now()
        if self.status == self.Status.TRIALING:
            if self.trial_ends_at and now > self.trial_ends_at:
                return False
            return True
        if self.status in {self.Status.ACTIVE, self.Status.FREE}:
            return self.current_period_end is None or now < self.current_period_end
        if self.status == self.Status.PAST_DUE and self.grace_period_ends_at:
            return now < self.grace_period_ends_at
        return False

    
    def seats_used(self):
        if self.customer.organization_id:
            return self.customer.organization.memberships.filter(is_active=True).count()
        return 1

    
    def seats_available(self):
        return max(self.seat_limit - self.seats_used, 0)


class Entitlement(models.Model):
    """Feature flag/limit granted by plan or subscription override."""
    class ValueType(models.TextChoices):
        BOOLEAN = "boolean", _("Boolean")
        INTEGER = "integer", _("Integer")
        STRING = "string", _("String")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, null=True, blank=True, related_name="entitlements")
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, null=True, blank=True, related_name="entitlements")
    key = models.CharField(max_length=140)
    value_type = models.CharField(max_length=16, choices=ValueType.choices, default=ValueType.BOOLEAN)
    bool_value = models.BooleanField(default=False)
    int_value = models.IntegerField(null=True, blank=True)
    str_value = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["key"]), models.Index(fields=["plan", "key"]), models.Index(fields=["subscription", "key"])]
        constraints = [
            models.UniqueConstraint(fields=["plan", "key"], name="uniq_plan_entitlement_key"),
            models.UniqueConstraint(fields=["subscription", "key"], name="uniq_subscription_entitlement_key"),
        ]

    def __str__(self):
        return self.key

    @property
    def value(self):
        if self.value_type == self.ValueType.INTEGER:
            return self.int_value
        if self.value_type == self.ValueType.STRING:
            return self.str_value
        return self.bool_value


class Invoice(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", _("Draft")
        OPEN = "open", _("Open")
        PAID = "paid", _("Paid")
        VOID = "void", _("Void")
        UNCOLLECTIBLE = "uncollectible", _("Uncollectible")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(BillingCustomer, on_delete=models.CASCADE, related_name="invoices")
    subscription = models.ForeignKey(Subscription, on_delete=models.SET_NULL, null=True, blank=True, related_name="invoices")
    provider = models.CharField(max_length=40, default="manual")
    provider_invoice_id = models.CharField(max_length=180, blank=True)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.DRAFT)
    currency = models.CharField(max_length=3, default="USD")
    amount_due_cents = models.PositiveIntegerField(default=0)
    amount_paid_cents = models.PositiveIntegerField(default=0)
    hosted_invoice_url = models.URLField(blank=True)
    due_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["customer", "created_at"]), models.Index(fields=["provider", "provider_invoice_id"]), models.Index(fields=["status"])]

    def __str__(self):
        return f"invoice:{self.status}:{self.amount_due_cents}{self.currency}"


class PaymentTransaction(models.Model):
    class Status(models.TextChoices):
        REQUIRES_ACTION = "requires_action", _("Requires action")
        PROCESSING = "processing", _("Processing")
        SUCCEEDED = "succeeded", _("Succeeded")
        FAILED = "failed", _("Failed")
        REFUNDED = "refunded", _("Refunded")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(BillingCustomer, on_delete=models.CASCADE, related_name="payment_transactions")
    invoice = models.ForeignKey(Invoice, on_delete=models.SET_NULL, null=True, blank=True, related_name="transactions")
    provider = models.CharField(max_length=40, default="manual")
    provider_payment_id = models.CharField(max_length=180, blank=True)
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.PROCESSING)
    currency = models.CharField(max_length=3, default="USD")
    amount_cents = models.PositiveIntegerField(default=0)
    failure_code = models.CharField(max_length=80, blank=True)
    failure_message = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["customer", "created_at"]), models.Index(fields=["provider", "provider_payment_id"]), models.Index(fields=["status"])]

    def __str__(self):
        return f"payment:{self.status}:{self.amount_cents}{self.currency}"


class BillingWebhookEvent(models.Model):
    """Idempotent provider webhook log. Payload is retained for audit/replay."""
    class Status(models.TextChoices):
        RECEIVED = "received", _("Received")
        PROCESSED = "processed", _("Processed")
        FAILED = "failed", _("Failed")
        IGNORED = "ignored", _("Ignored")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.CharField(max_length=40)
    event_id = models.CharField(max_length=180)
    event_type = models.CharField(max_length=120)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.RECEIVED)
    payload = models.JSONField(default=dict)
    signature_valid = models.BooleanField(default=False)
    processed_at = models.DateTimeField(null=True, blank=True)
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("provider", "event_id")]
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["provider", "event_id"]), models.Index(fields=["event_type"]), models.Index(fields=["status"])]

    def __str__(self):
        return f"webhook:{self.provider}:{self.event_type}:{self.status}"


class CheckoutSession(models.Model):
    """Provider checkout session created for a tenant/user purchase."""
    class Status(models.TextChoices):
        CREATED = "created", _("Created")
        OPEN = "open", _("Open")
        COMPLETED = "completed", _("Completed")
        EXPIRED = "expired", _("Expired")
        FAILED = "failed", _("Failed")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(BillingCustomer, on_delete=models.CASCADE, related_name="checkout_sessions")
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="checkout_sessions")
    price = models.ForeignKey(Price, on_delete=models.PROTECT, related_name="checkout_sessions")
    provider = models.CharField(max_length=40, default="stripe")
    provider_session_id = models.CharField(max_length=220, blank=True, db_index=True)
    checkout_url = models.URLField(blank=True)
    success_url = models.URLField()
    cancel_url = models.URLField()
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.CREATED)
    metadata = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="billing_checkout_sessions_created")
    expires_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["customer", "status"]),
            models.Index(fields=["provider", "provider_session_id"]),
            models.Index(fields=["created_by", "created_at"]),
        ]

    def __str__(self):
        return f"checkout:{self.provider}:{self.status}"


class CustomerPortalSession(models.Model):
    """Provider billing-portal session for customers to manage payment methods/subscriptions."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(BillingCustomer, on_delete=models.CASCADE, related_name="portal_sessions")
    provider = models.CharField(max_length=40, default="stripe")
    provider_session_id = models.CharField(max_length=220, blank=True, db_index=True)
    portal_url = models.URLField()
    return_url = models.URLField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="billing_portal_sessions_created")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["customer", "created_at"]), models.Index(fields=["provider", "provider_session_id"])]

    def __str__(self):
        return f"portal:{self.provider}:{self.customer_id}"


class SubscriptionChangeRequest(models.Model):
    """Admin/user requested lifecycle operation for a subscription."""
    class Action(models.TextChoices):
        CHANGE_PLAN = "change_plan", _("Change plan")
        CHANGE_QUANTITY = "change_quantity", _("Change quantity")
        CANCEL_AT_PERIOD_END = "cancel_at_period_end", _("Cancel at period end")
        CANCEL_NOW = "cancel_now", _("Cancel immediately")
        RESUME = "resume", _("Resume")
        EXTEND_TRIAL = "extend_trial", _("Extend trial")
        EXTEND_GRACE = "extend_grace", _("Extend grace period")

    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        APPLIED = "applied", _("Applied")
        FAILED = "failed", _("Failed")
        CANCELLED = "cancelled", _("Cancelled")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name="change_requests")
    action = models.CharField(max_length=40, choices=Action.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    target_plan = models.ForeignKey(Plan, on_delete=models.PROTECT, null=True, blank=True, related_name="subscription_change_targets")
    target_price = models.ForeignKey(Price, on_delete=models.PROTECT, null=True, blank=True, related_name="subscription_change_targets")
    target_quantity = models.PositiveIntegerField(null=True, blank=True)
    effective_at = models.DateTimeField(null=True, blank=True)
    applied_at = models.DateTimeField(null=True, blank=True)
    provider = models.CharField(max_length=40, default="manual")
    provider_change_id = models.CharField(max_length=180, blank=True)
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="billing_subscription_changes_requested")
    reason = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["subscription", "status"]),
            models.Index(fields=["action", "status"]),
            models.Index(fields=["effective_at"]),
        ]

    def __str__(self):
        return f"subscription-change:{self.action}:{self.status}"


class UsageMetric(models.Model):
    """Meterable unit used for usage-based limits and future usage billing."""
    class Aggregation(models.TextChoices):
        SUM = "sum", _("Sum")
        MAX = "max", _("Max")
        LAST = "last", _("Last")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, null=True, blank=True, related_name="usage_metrics")
    code = models.SlugField(max_length=120, unique=True)
    name = models.CharField(max_length=180)
    unit = models.CharField(max_length=40, default="unit")
    aggregation = models.CharField(max_length=16, choices=Aggregation.choices, default=Aggregation.SUM)
    entitlement_key = models.CharField(max_length=140, help_text="Entitlement key that defines the allowed limit, e.g. api.requests.monthly.max")
    is_active = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["code"]
        indexes = [models.Index(fields=["code"]), models.Index(fields=["project", "is_active"]), models.Index(fields=["entitlement_key"])]

    def __str__(self):
        return self.code


class UsageRecord(models.Model):
    """Append-only usage ledger tied to a billing customer and metric."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(BillingCustomer, on_delete=models.CASCADE, related_name="usage_records")
    metric = models.ForeignKey(UsageMetric, on_delete=models.PROTECT, related_name="records")
    quantity = models.PositiveIntegerField(default=1)
    idempotency_key = models.CharField(max_length=180, blank=True)
    source = models.CharField(max_length=80, default="api")
    occurred_at = models.DateTimeField(default=timezone.now)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-occurred_at"]
        constraints = [models.UniqueConstraint(fields=["customer", "metric", "idempotency_key"], name="uniq_usage_idempotency_key")]
        indexes = [
            models.Index(fields=["customer", "metric", "occurred_at"]),
            models.Index(fields=["metric", "occurred_at"]),
            models.Index(fields=["source"]),
        ]

    def __str__(self):
        return f"usage:{self.metric.code}:{self.quantity}"


class BillingProfile(models.Model):
    """Structured customer billing details for invoices, tax, and provider sync."""
    class TaxExemptStatus(models.TextChoices):
        NONE = "none", _("None")
        EXEMPT = "exempt", _("Exempt")
        REVERSE = "reverse", _("Reverse charge")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.OneToOneField(BillingCustomer, on_delete=models.CASCADE, related_name="profile")
    legal_name = models.CharField(max_length=220, blank=True)
    billing_email = models.EmailField(blank=True)
    phone = models.CharField(max_length=60, blank=True)
    address_line1 = models.CharField(max_length=220, blank=True)
    address_line2 = models.CharField(max_length=220, blank=True)
    city = models.CharField(max_length=120, blank=True)
    state = models.CharField(max_length=120, blank=True)
    postal_code = models.CharField(max_length=40, blank=True)
    country = models.CharField(max_length=2, blank=True, help_text="ISO-3166 alpha-2 country code.")
    tax_exempt_status = models.CharField(max_length=24, choices=TaxExemptStatus.choices, default=TaxExemptStatus.NONE)
    default_currency = models.CharField(max_length=3, default="USD")
    invoice_prefix = models.CharField(max_length=20, blank=True)
    next_invoice_number = models.PositiveIntegerField(default=1)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["country"]), models.Index(fields=["tax_exempt_status"])]

    def __str__(self):
        return f"billing-profile:{self.customer_id}"


class CustomerTaxId(models.Model):
    """Tax registration IDs, e.g. VAT/GST/EIN, synced to payment providers when needed."""
    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        VERIFIED = "verified", _("Verified")
        UNVERIFIED = "unverified", _("Unverified")
        REJECTED = "rejected", _("Rejected")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(BillingCustomer, on_delete=models.CASCADE, related_name="tax_ids")
    tax_type = models.CharField(max_length=40, help_text="Provider/type code such as eu_vat, gb_vat, us_ein, gst.")
    value = models.CharField(max_length=100)
    country = models.CharField(max_length=2, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    provider = models.CharField(max_length=40, default="manual")
    provider_tax_id = models.CharField(max_length=180, blank=True)
    is_default = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_default", "-created_at"]
        indexes = [models.Index(fields=["customer", "status"]), models.Index(fields=["provider", "provider_tax_id"]), models.Index(fields=["tax_type", "country"])]
        constraints = [models.UniqueConstraint(fields=["customer", "tax_type", "value"], name="uniq_customer_tax_id_value")]

    def __str__(self):
        return f"tax-id:{self.tax_type}:{self.status}"


class CreditNote(models.Model):
    """Credit note attached to an invoice for refunds, adjustments, or goodwill credits."""
    class Reason(models.TextChoices):
        DUPLICATE = "duplicate", _("Duplicate")
        FRAUDULENT = "fraudulent", _("Fraudulent")
        REQUESTED_BY_CUSTOMER = "requested_by_customer", _("Requested by customer")
        SERVICE_CREDIT = "service_credit", _("Service credit")
        PRICE_ADJUSTMENT = "price_adjustment", _("Price adjustment")
        OTHER = "other", _("Other")

    class Status(models.TextChoices):
        DRAFT = "draft", _("Draft")
        ISSUED = "issued", _("Issued")
        VOID = "void", _("Void")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(BillingCustomer, on_delete=models.CASCADE, related_name="credit_notes")
    invoice = models.ForeignKey(Invoice, on_delete=models.SET_NULL, null=True, blank=True, related_name="credit_notes")
    number = models.CharField(max_length=60, unique=True)
    reason = models.CharField(max_length=40, choices=Reason.choices, default=Reason.OTHER)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    currency = models.CharField(max_length=3, default="USD")
    amount_cents = models.PositiveIntegerField(default=0)
    provider = models.CharField(max_length=40, default="manual")
    provider_credit_note_id = models.CharField(max_length=180, blank=True)
    memo = models.TextField(blank=True)
    issued_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="billing_credit_notes_issued")
    issued_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["customer", "status"]), models.Index(fields=["provider", "provider_credit_note_id"]), models.Index(fields=["number"])]

    def __str__(self):
        return f"credit-note:{self.number}:{self.status}"


class RefundRequest(models.Model):
    """Governed refund workflow before provider-side refund execution."""
    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        APPROVED = "approved", _("Approved")
        REJECTED = "rejected", _("Rejected")
        PROCESSED = "processed", _("Processed")
        FAILED = "failed", _("Failed")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(BillingCustomer, on_delete=models.CASCADE, related_name="refund_requests")
    payment = models.ForeignKey(PaymentTransaction, on_delete=models.SET_NULL, null=True, blank=True, related_name="refund_requests")
    invoice = models.ForeignKey(Invoice, on_delete=models.SET_NULL, null=True, blank=True, related_name="refund_requests")
    credit_note = models.ForeignKey(CreditNote, on_delete=models.SET_NULL, null=True, blank=True, related_name="refund_requests")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    currency = models.CharField(max_length=3, default="USD")
    amount_cents = models.PositiveIntegerField(default=0)
    reason = models.TextField(blank=True)
    provider = models.CharField(max_length=40, default="manual")
    provider_refund_id = models.CharField(max_length=180, blank=True)
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="billing_refunds_requested")
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="billing_refunds_reviewed")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    error = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["customer", "status"]), models.Index(fields=["provider", "provider_refund_id"]), models.Index(fields=["created_at"])]

    def __str__(self):
        return f"refund:{self.status}:{self.amount_cents}{self.currency}"


class DunningCase(models.Model):
    """Collections case for past-due subscriptions and failed invoice/payment events."""
    class Status(models.TextChoices):
        OPEN = "open", _("Open")
        IN_GRACE = "in_grace", _("In grace")
        RESTRICTED = "restricted", _("Restricted")
        RESOLVED = "resolved", _("Resolved")
        CANCELLED = "cancelled", _("Cancelled")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(BillingCustomer, on_delete=models.CASCADE, related_name="dunning_cases")
    subscription = models.ForeignKey(Subscription, on_delete=models.SET_NULL, null=True, blank=True, related_name="dunning_cases")
    invoice = models.ForeignKey(Invoice, on_delete=models.SET_NULL, null=True, blank=True, related_name="dunning_cases")
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.OPEN)
    failed_attempts = models.PositiveIntegerField(default=0)
    last_failure_at = models.DateTimeField(null=True, blank=True)
    next_retry_at = models.DateTimeField(null=True, blank=True)
    grace_ends_at = models.DateTimeField(null=True, blank=True)
    restricted_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_note = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["customer", "status"]), models.Index(fields=["next_retry_at"]), models.Index(fields=["grace_ends_at"])]

    def __str__(self):
        return f"dunning:{self.customer_id}:{self.status}"


class Discount(models.Model):
    """Reusable discount rule for checkout, manual grants, and admin promotions."""
    class DiscountType(models.TextChoices):
        PERCENT = "percent", _("Percent")
        FIXED = "fixed", _("Fixed amount")
        FREE = "free", _("Free override")

    class Duration(models.TextChoices):
        ONCE = "once", _("Once")
        REPEATING = "repeating", _("Repeating")
        FOREVER = "forever", _("Forever")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.SlugField(max_length=120, unique=True)
    name = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    discount_type = models.CharField(max_length=20, choices=DiscountType.choices)
    percent_off = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    amount_off_cents = models.PositiveIntegerField(null=True, blank=True)
    currency = models.CharField(max_length=3, default="USD")
    duration = models.CharField(max_length=20, choices=Duration.choices, default=Duration.ONCE)
    duration_months = models.PositiveIntegerField(null=True, blank=True)
    max_redemptions = models.PositiveIntegerField(null=True, blank=True)
    redeemed_count = models.PositiveIntegerField(default=0)
    applies_to_projects = models.ManyToManyField(Project, blank=True, related_name="discounts")
    applies_to_plans = models.ManyToManyField(Plan, blank=True, related_name="discounts")
    starts_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="billing_discounts_created")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["code"]
        indexes = [
            models.Index(fields=["code", "is_active"]),
            models.Index(fields=["starts_at", "expires_at"]),
            models.Index(fields=["discount_type"]),
        ]

    def __str__(self):
        return self.code

    @property
    def is_redeemable(self):
        now = timezone.now()
        if not self.is_active:
            return False
        if self.starts_at and now < self.starts_at:
            return False
        if self.expires_at and now >= self.expires_at:
            return False
        if self.max_redemptions is not None and self.redeemed_count >= self.max_redemptions:
            return False
        return True

    def applies_to_price(self, price: Price) -> bool:
        if self.applies_to_plans.exists() and not self.applies_to_plans.filter(pk=price.plan_id).exists():
            return False
        if self.applies_to_projects.exists() and not self.applies_to_projects.filter(pk=price.plan.project_id).exists():
            return False
        return True

    def calculate_amount_cents(self, amount_cents: int) -> int:
        if self.discount_type == self.DiscountType.FREE:
            return amount_cents
        if self.discount_type == self.DiscountType.FIXED:
            return min(self.amount_off_cents or 0, amount_cents)
        if self.discount_type == self.DiscountType.PERCENT:
            return int((amount_cents * float(self.percent_off or 0)) / 100)
        return 0


class PromotionCode(models.Model):
    """Customer-facing code that maps to a discount and optional tenant/project restrictions."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=120, unique=True)
    discount = models.ForeignKey(Discount, on_delete=models.CASCADE, related_name="promotion_codes")
    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, null=True, blank=True, related_name="promotion_codes")
    is_active = models.BooleanField(default=True)
    max_redemptions = models.PositiveIntegerField(null=True, blank=True)
    redeemed_count = models.PositiveIntegerField(default=0)
    expires_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["code"]
        indexes = [models.Index(fields=["code", "is_active"]), models.Index(fields=["organization", "is_active"])]

    def __str__(self):
        return self.code

    @property
    def is_redeemable(self):
        now = timezone.now()
        if not self.is_active or not self.discount.is_redeemable:
            return False
        if self.expires_at and now >= self.expires_at:
            return False
        if self.max_redemptions is not None and self.redeemed_count >= self.max_redemptions:
            return False
        return True


class DiscountRedemption(models.Model):
    """Append-only redemption ledger for fraud review, idempotency, and customer support."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    discount = models.ForeignKey(Discount, on_delete=models.PROTECT, related_name="redemptions")
    promotion_code = models.ForeignKey(PromotionCode, on_delete=models.PROTECT, null=True, blank=True, related_name="redemptions")
    customer = models.ForeignKey(BillingCustomer, on_delete=models.CASCADE, related_name="discount_redemptions")
    subscription = models.ForeignKey(Subscription, on_delete=models.SET_NULL, null=True, blank=True, related_name="discount_redemptions")
    price = models.ForeignKey(Price, on_delete=models.SET_NULL, null=True, blank=True, related_name="discount_redemptions")
    idempotency_key = models.CharField(max_length=180, blank=True)
    original_amount_cents = models.PositiveIntegerField(default=0)
    discount_amount_cents = models.PositiveIntegerField(default=0)
    final_amount_cents = models.PositiveIntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)
    redeemed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="billing_discounts_redeemed")
    redeemed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-redeemed_at"]
        indexes = [models.Index(fields=["customer", "redeemed_at"]), models.Index(fields=["discount", "redeemed_at"])]
        constraints = [models.UniqueConstraint(fields=["customer", "discount", "idempotency_key"], name="uniq_discount_redemption_idempotency")]

    def __str__(self):
        return f"discount-redemption:{self.discount.code}:{self.discount_amount_cents}"


class AddOn(models.Model):
    """Billable add-on that can extend a subscription with extra seats, quota, or features."""
    class BillingMode(models.TextChoices):
        RECURRING = "recurring", _("Recurring")
        ONE_TIME = "one_time", _("One time")
        METERED = "metered", _("Metered")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.PROTECT, null=True, blank=True, related_name="addons")
    code = models.SlugField(max_length=120, unique=True)
    name = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    billing_mode = models.CharField(max_length=20, choices=BillingMode.choices, default=BillingMode.RECURRING)
    currency = models.CharField(max_length=3, default="USD")
    unit_amount_cents = models.PositiveIntegerField(default=0)
    provider_price_id = models.CharField(max_length=180, blank=True)
    is_active = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["code"]
        indexes = [models.Index(fields=["code", "is_active"]), models.Index(fields=["project", "is_active"])]

    def __str__(self):
        return self.code


class AddOnEntitlement(models.Model):
    """Entitlement contribution granted by an add-on unit."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    addon = models.ForeignKey(AddOn, on_delete=models.CASCADE, related_name="entitlements")
    key = models.CharField(max_length=140)
    value_type = models.CharField(max_length=16, choices=Entitlement.ValueType.choices, default=Entitlement.ValueType.INTEGER)
    bool_value = models.BooleanField(default=False)
    int_value = models.IntegerField(null=True, blank=True)
    str_value = models.CharField(max_length=255, blank=True)
    is_incremental = models.BooleanField(default=True, help_text="When true, integer values are multiplied by quantity and added to the base entitlement.")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["addon", "key"])]
        constraints = [models.UniqueConstraint(fields=["addon", "key"], name="uniq_addon_entitlement_key")]

    @property
    def value(self):
        if self.value_type == Entitlement.ValueType.INTEGER:
            return self.int_value
        if self.value_type == Entitlement.ValueType.STRING:
            return self.str_value
        return self.bool_value

    def __str__(self):
        return f"{self.addon.code}:{self.key}"


class SubscriptionAddOn(models.Model):
    """Add-on attached to a subscription with provider sync metadata."""
    class Status(models.TextChoices):
        ACTIVE = "active", _("Active")
        PAUSED = "paused", _("Paused")
        CANCELLED = "cancelled", _("Cancelled")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name="addons")
    addon = models.ForeignKey(AddOn, on_delete=models.PROTECT, related_name="subscription_addons")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    quantity = models.PositiveIntegerField(default=1)
    unit_amount_cents = models.PositiveIntegerField(default=0)
    provider = models.CharField(max_length=40, default="manual")
    provider_subscription_item_id = models.CharField(max_length=180, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="billing_subscription_addons_created")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["subscription", "addon__code"]
        indexes = [models.Index(fields=["subscription", "status"]), models.Index(fields=["addon", "status"]), models.Index(fields=["provider", "provider_subscription_item_id"])]
        constraints = [models.UniqueConstraint(fields=["subscription", "addon"], name="uniq_subscription_addon")]

    def __str__(self):
        return f"subscription-addon:{self.subscription_id}:{self.addon.code}"


class EntitlementSnapshot(models.Model):
    """Cached entitlement payload used by product apps for fast, auditable access checks."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.OneToOneField(BillingCustomer, on_delete=models.CASCADE, related_name="entitlement_snapshot")
    payload = models.JSONField(default=dict)
    version = models.PositiveIntegerField(default=1)
    calculated_at = models.DateTimeField(default=timezone.now)
    invalidated_at = models.DateTimeField(null=True, blank=True)
    reason = models.CharField(max_length=180, blank=True)

    class Meta:
        indexes = [models.Index(fields=["calculated_at"]), models.Index(fields=["invalidated_at"])]

    def __str__(self):
        return f"entitlement-snapshot:{self.customer_id}:v{self.version}"


class BillingOutboxEvent(models.Model):
    """Transactional outbox for reliable async billing/provider side effects."""
    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        PROCESSING = "processing", _("Processing")
        DISPATCHED = "dispatched", _("Dispatched")
        FAILED = "failed", _("Failed")
        CANCELLED = "cancelled", _("Cancelled")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_type = models.CharField(max_length=160)
    aggregate_type = models.CharField(max_length=80, blank=True)
    aggregate_id = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    payload = models.JSONField(default=dict, blank=True)
    headers = models.JSONField(default=dict, blank=True)
    idempotency_key = models.CharField(max_length=180, blank=True)
    attempts = models.PositiveIntegerField(default=0)
    max_attempts = models.PositiveIntegerField(default=8)
    next_attempt_at = models.DateTimeField(default=timezone.now)
    locked_at = models.DateTimeField(null=True, blank=True)
    dispatched_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["next_attempt_at", "created_at"]
        indexes = [
            models.Index(fields=["status", "next_attempt_at"]),
            models.Index(fields=["event_type", "created_at"]),
            models.Index(fields=["aggregate_type", "aggregate_id"]),
            models.Index(fields=["idempotency_key"]),
        ]
        constraints = [
            models.UniqueConstraint(fields=["event_type", "idempotency_key"], condition=~models.Q(idempotency_key=""), name="uniq_billing_outbox_event_idempotency"),
        ]

    def __str__(self):
        return f"outbox:{self.event_type}:{self.status}"


class ProviderSyncState(models.Model):
    """Provider sync cursor/health record used by reconciliation jobs."""
    class Status(models.TextChoices):
        HEALTHY = "healthy", _("Healthy")
        DEGRADED = "degraded", _("Degraded")
        FAILING = "failing", _("Failing")
        DISABLED = "disabled", _("Disabled")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.CharField(max_length=40)
    resource_type = models.CharField(max_length=80)
    cursor = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.HEALTHY)
    last_started_at = models.DateTimeField(null=True, blank=True)
    last_success_at = models.DateTimeField(null=True, blank=True)
    last_failure_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)
    error_count = models.PositiveIntegerField(default=0)
    lag_seconds = models.PositiveIntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["provider", "resource_type"]
        indexes = [models.Index(fields=["provider", "resource_type"]), models.Index(fields=["status"])]
        constraints = [models.UniqueConstraint(fields=["provider", "resource_type"], name="uniq_provider_sync_resource")]

    def __str__(self):
        return f"sync:{self.provider}:{self.resource_type}:{self.status}"


class WebhookReplayRequest(models.Model):
    """Operator-controlled replay record for provider webhook events."""
    class Status(models.TextChoices):
        REQUESTED = "requested", _("Requested")
        REPLAYED = "replayed", _("Replayed")
        FAILED = "failed", _("Failed")
        CANCELLED = "cancelled", _("Cancelled")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    webhook_event = models.ForeignKey(BillingWebhookEvent, on_delete=models.CASCADE, related_name="replay_requests")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.REQUESTED)
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="billing_webhook_replays_requested")
    reason = models.TextField(blank=True)
    replayed_at = models.DateTimeField(null=True, blank=True)
    error = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "created_at"]), models.Index(fields=["webhook_event", "status"])]

    def __str__(self):
        return f"webhook-replay:{self.webhook_event_id}:{self.status}"


class EntitlementChangeLog(models.Model):
    """Append-only history of entitlement snapshot changes for audit/debugging."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(BillingCustomer, on_delete=models.CASCADE, related_name="entitlement_change_logs")
    snapshot = models.ForeignKey(EntitlementSnapshot, on_delete=models.SET_NULL, null=True, blank=True, related_name="change_logs")
    previous_payload = models.JSONField(default=dict, blank=True)
    new_payload = models.JSONField(default=dict, blank=True)
    reason = models.CharField(max_length=180, blank=True)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="billing_entitlement_changes")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["customer", "created_at"]), models.Index(fields=["reason", "created_at"])]

    def __str__(self):
        return f"entitlement-change:{self.customer_id}:{self.reason}"
