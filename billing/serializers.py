from rest_framework import serializers

from accounts.models import Organization
from .models import (
    BillingCustomer, BillingProfile, BillingWebhookEvent, CheckoutSession, CreditNote,
    CustomerPortalSession, CustomerTaxId, DunningCase, Entitlement, Invoice,
    PaymentTransaction, Plan, Price, Project, RefundRequest, Subscription,
    SubscriptionChangeRequest, UsageMetric, UsageRecord,
    Discount, PromotionCode, DiscountRedemption, AddOn, AddOnEntitlement,
    SubscriptionAddOn, EntitlementSnapshot, BillingOutboxEvent, ProviderSyncState, WebhookReplayRequest, EntitlementChangeLog,
)
from .services import build_customer_entitlements, grant_manual_subscription, redeem_discount, attach_subscription_addon, recalculate_entitlement_snapshot


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ["id", "code", "name", "description", "is_active", "metadata", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class PriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Price
        fields = ["id", "plan", "code", "currency", "amount_cents", "interval", "is_active", "is_custom", "provider_price_id", "metadata", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class EntitlementSerializer(serializers.ModelSerializer):
    value = serializers.SerializerMethodField()

    class Meta:
        model = Entitlement
        fields = ["id", "plan", "subscription", "key", "value_type", "bool_value", "int_value", "str_value", "value", "metadata", "created_at", "updated_at"]
        read_only_fields = ["id", "value", "created_at", "updated_at"]

    def get_value(self, obj):
        return obj.value

    def validate(self, attrs):
        plan = attrs.get("plan", getattr(self.instance, "plan", None))
        subscription = attrs.get("subscription", getattr(self.instance, "subscription", None))
        if bool(plan) == bool(subscription):
            raise serializers.ValidationError("Exactly one of plan or subscription must be set.")
        return attrs


class PlanSerializer(serializers.ModelSerializer):
    prices = PriceSerializer(many=True, read_only=True)
    entitlements = EntitlementSerializer(many=True, read_only=True)

    class Meta:
        model = Plan
        fields = ["id", "project", "code", "name", "description", "visibility", "is_active", "trial_days", "metadata", "prices", "entitlements", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def create(self, validated_data):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["created_by"] = request.user
        return super().create(validated_data)


class BillingCustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = BillingCustomer
        fields = ["id", "organization", "user", "billing_email", "billing_name", "provider", "provider_customer_id", "tax_id", "metadata", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class SubscriptionSerializer(serializers.ModelSerializer):
    plan_code = serializers.CharField(source="plan.code", read_only=True)
    project_code = serializers.CharField(source="plan.project.code", read_only=True, allow_null=True)
    effective_entitlements = serializers.SerializerMethodField()

    class Meta:
        model = Subscription
        fields = ["id", "customer", "plan", "plan_code", "project_code", "price", "status", "quantity", "seat_limit", "trial_ends_at", "grace_period_ends_at", "current_period_start", "current_period_end", "cancel_at_period_end", "cancelled_at", "provider", "provider_subscription_id", "admin_note", "effective_entitlements", "created_at", "updated_at"]
        read_only_fields = ["id", "provider", "provider_subscription_id", "effective_entitlements", "created_at", "updated_at"]

    def get_effective_entitlements(self, obj):
        from .services import build_effective_entitlements
        return build_effective_entitlements(obj)


class ManualSubscriptionGrantSerializer(serializers.Serializer):
    organization_slug = serializers.SlugField()
    plan_code = serializers.SlugField()
    price_code = serializers.SlugField(required=False, allow_blank=True)
    status = serializers.ChoiceField(choices=Subscription.Status.choices, default=Subscription.Status.FREE)
    current_period_end = serializers.DateTimeField(required=False, allow_null=True)
    admin_note = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        try:
            attrs["organization"] = Organization.objects.get(slug=attrs["organization_slug"], is_active=True)
        except Organization.DoesNotExist as exc:
            raise serializers.ValidationError({"organization_slug": "Organization not found."}) from exc
        try:
            attrs["plan"] = Plan.objects.get(code=attrs["plan_code"], is_active=True)
        except Plan.DoesNotExist as exc:
            raise serializers.ValidationError({"plan_code": "Plan not found."}) from exc
        price_code = attrs.get("price_code")
        if price_code:
            try:
                attrs["price"] = Price.objects.get(code=price_code, plan=attrs["plan"], is_active=True)
            except Price.DoesNotExist as exc:
                raise serializers.ValidationError({"price_code": "Price not found for this plan."}) from exc
        return attrs

    def save(self, **kwargs):
        request = self.context["request"]
        return grant_manual_subscription(
            organization=self.validated_data["organization"],
            plan=self.validated_data["plan"],
            price=self.validated_data.get("price"),
            status=self.validated_data["status"],
            current_period_end=self.validated_data.get("current_period_end"),
            admin_note=self.validated_data.get("admin_note", ""),
            actor=request.user,
        )


class CustomerEntitlementsSerializer(serializers.Serializer):
    organization_slug = serializers.SlugField(required=False)

    def get_entitlements(self, customer):
        return build_customer_entitlements(customer)


class InvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class PaymentTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentTransaction
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class BillingWebhookEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = BillingWebhookEvent
        fields = "__all__"
        read_only_fields = ["id", "created_at", "processed_at"]


class CheckoutSessionSerializer(serializers.ModelSerializer):
    plan_code = serializers.CharField(source="plan.code", read_only=True)
    price_code = serializers.CharField(source="price.code", read_only=True)

    class Meta:
        model = CheckoutSession
        fields = ["id", "customer", "plan", "plan_code", "price", "price_code", "provider", "provider_session_id", "checkout_url", "success_url", "cancel_url", "status", "metadata", "expires_at", "completed_at", "created_at", "updated_at"]
        read_only_fields = ["id", "provider", "provider_session_id", "checkout_url", "status", "metadata", "expires_at", "completed_at", "created_at", "updated_at"]


class CreateCheckoutSessionSerializer(serializers.Serializer):
    organization_slug = serializers.SlugField()
    price_code = serializers.SlugField()
    success_url = serializers.URLField()
    cancel_url = serializers.URLField()

    def validate(self, attrs):
        try:
            attrs["organization"] = Organization.objects.get(slug=attrs["organization_slug"], is_active=True)
        except Organization.DoesNotExist as exc:
            raise serializers.ValidationError({"organization_slug": "Organization not found."}) from exc
        try:
            attrs["price"] = Price.objects.select_related("plan", "plan__project").get(code=attrs["price_code"], is_active=True, plan__is_active=True)
        except Price.DoesNotExist as exc:
            raise serializers.ValidationError({"price_code": "Active price not found."}) from exc
        return attrs


class CustomerPortalSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerPortalSession
        fields = ["id", "customer", "provider", "provider_session_id", "portal_url", "return_url", "created_at"]
        read_only_fields = ["id", "customer", "provider", "provider_session_id", "portal_url", "created_at"]


class CreateCustomerPortalSessionSerializer(serializers.Serializer):
    organization_slug = serializers.SlugField()
    return_url = serializers.URLField()

    def validate(self, attrs):
        try:
            attrs["organization"] = Organization.objects.get(slug=attrs["organization_slug"], is_active=True)
        except Organization.DoesNotExist as exc:
            raise serializers.ValidationError({"organization_slug": "Organization not found."}) from exc
        return attrs


class SubscriptionChangeRequestSerializer(serializers.ModelSerializer):
    subscription_status = serializers.CharField(source="subscription.status", read_only=True)

    class Meta:
        model = SubscriptionChangeRequest
        fields = [
            "id", "subscription", "subscription_status", "action", "status", "target_plan", "target_price",
            "target_quantity", "effective_at", "applied_at", "provider", "provider_change_id", "requested_by",
            "reason", "metadata", "error", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "status", "applied_at", "provider", "provider_change_id", "requested_by", "error", "created_at", "updated_at"]

    def validate(self, attrs):
        action = attrs.get("action")
        if action == SubscriptionChangeRequest.Action.CHANGE_PLAN and not attrs.get("target_plan"):
            raise serializers.ValidationError({"target_plan": "Required for change_plan."})
        if action == SubscriptionChangeRequest.Action.CHANGE_QUANTITY and not attrs.get("target_quantity"):
            raise serializers.ValidationError({"target_quantity": "Required for change_quantity."})
        if action in {SubscriptionChangeRequest.Action.EXTEND_TRIAL, SubscriptionChangeRequest.Action.EXTEND_GRACE} and not attrs.get("effective_at"):
            raise serializers.ValidationError({"effective_at": "Required for trial/grace extension."})
        return attrs


class UsageMetricSerializer(serializers.ModelSerializer):
    class Meta:
        model = UsageMetric
        fields = ["id", "project", "code", "name", "unit", "aggregation", "entitlement_key", "is_active", "metadata", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class UsageRecordSerializer(serializers.ModelSerializer):
    metric_code = serializers.CharField(source="metric.code", read_only=True)

    class Meta:
        model = UsageRecord
        fields = ["id", "customer", "metric", "metric_code", "quantity", "idempotency_key", "source", "occurred_at", "metadata", "created_at"]
        read_only_fields = ["id", "created_at"]


class RecordUsageSerializer(serializers.Serializer):
    organization_slug = serializers.SlugField()
    metric_code = serializers.SlugField()
    quantity = serializers.IntegerField(min_value=1, default=1)
    idempotency_key = serializers.CharField(required=False, allow_blank=True, max_length=180)
    source = serializers.CharField(required=False, default="api", max_length=80)
    metadata = serializers.JSONField(required=False)

    def validate(self, attrs):
        try:
            attrs["organization"] = Organization.objects.get(slug=attrs["organization_slug"], is_active=True)
        except Organization.DoesNotExist as exc:
            raise serializers.ValidationError({"organization_slug": "Organization not found."}) from exc
        try:
            attrs["metric"] = UsageMetric.objects.get(code=attrs["metric_code"], is_active=True)
        except UsageMetric.DoesNotExist as exc:
            raise serializers.ValidationError({"metric_code": "Usage metric not found."}) from exc
        return attrs


class BillingProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = BillingProfile
        fields = [
            "id", "customer", "legal_name", "billing_email", "phone", "address_line1", "address_line2",
            "city", "state", "postal_code", "country", "tax_exempt_status", "default_currency",
            "invoice_prefix", "next_invoice_number", "metadata", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "next_invoice_number", "created_at", "updated_at"]


class CustomerTaxIdSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerTaxId
        fields = [
            "id", "customer", "tax_type", "value", "country", "status", "provider", "provider_tax_id",
            "is_default", "metadata", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "provider_tax_id", "created_at", "updated_at"]


class CreditNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreditNote
        fields = [
            "id", "customer", "invoice", "number", "reason", "status", "currency", "amount_cents",
            "provider", "provider_credit_note_id", "memo", "issued_by", "issued_at", "metadata",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "number", "status", "provider_credit_note_id", "issued_by", "issued_at", "created_at", "updated_at"]


class CreateCreditNoteSerializer(serializers.Serializer):
    customer = serializers.PrimaryKeyRelatedField(queryset=BillingCustomer.objects.all())
    invoice = serializers.PrimaryKeyRelatedField(queryset=Invoice.objects.all(), required=False, allow_null=True)
    reason = serializers.ChoiceField(choices=CreditNote.Reason.choices, default=CreditNote.Reason.OTHER)
    currency = serializers.CharField(max_length=3, default="USD")
    amount_cents = serializers.IntegerField(min_value=1)
    memo = serializers.CharField(required=False, allow_blank=True)
    metadata = serializers.JSONField(required=False)


class RefundRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = RefundRequest
        fields = [
            "id", "customer", "payment", "invoice", "credit_note", "status", "currency", "amount_cents",
            "reason", "provider", "provider_refund_id", "requested_by", "reviewed_by", "reviewed_at",
            "processed_at", "error", "metadata", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "status", "provider_refund_id", "requested_by", "reviewed_by", "reviewed_at",
            "processed_at", "error", "created_at", "updated_at",
        ]

    def validate(self, attrs):
        if not attrs.get("payment") and not attrs.get("invoice"):
            raise serializers.ValidationError("Either payment or invoice must be supplied.")
        return attrs


class ReviewRefundSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["approve", "reject", "process"])
    note = serializers.CharField(required=False, allow_blank=True)
    provider_refund_id = serializers.CharField(required=False, allow_blank=True)


class DunningCaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = DunningCase
        fields = [
            "id", "customer", "subscription", "invoice", "status", "failed_attempts", "last_failure_at",
            "next_retry_at", "grace_ends_at", "restricted_at", "resolved_at", "resolution_note",
            "metadata", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class DiscountSerializer(serializers.ModelSerializer):
    is_redeemable = serializers.BooleanField(read_only=True)

    class Meta:
        model = Discount
        fields = [
            "id", "code", "name", "description", "discount_type", "percent_off", "amount_off_cents",
            "currency", "duration", "duration_months", "max_redemptions", "redeemed_count",
            "applies_to_projects", "applies_to_plans", "starts_at", "expires_at", "is_active",
            "is_redeemable", "metadata", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "redeemed_count", "is_redeemable", "created_at", "updated_at"]

    def validate(self, attrs):
        discount_type = attrs.get("discount_type", getattr(self.instance, "discount_type", None))
        if discount_type == Discount.DiscountType.PERCENT and attrs.get("percent_off") is None:
            raise serializers.ValidationError({"percent_off": "Required for percent discounts."})
        if discount_type == Discount.DiscountType.FIXED and attrs.get("amount_off_cents") is None:
            raise serializers.ValidationError({"amount_off_cents": "Required for fixed discounts."})
        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["created_by"] = request.user
        return super().create(validated_data)


class PromotionCodeSerializer(serializers.ModelSerializer):
    is_redeemable = serializers.BooleanField(read_only=True)
    discount_code = serializers.CharField(source="discount.code", read_only=True)

    class Meta:
        model = PromotionCode
        fields = ["id", "code", "discount", "discount_code", "organization", "is_active", "max_redemptions", "redeemed_count", "expires_at", "is_redeemable", "metadata", "created_at", "updated_at"]
        read_only_fields = ["id", "discount_code", "redeemed_count", "is_redeemable", "created_at", "updated_at"]


class DiscountRedemptionSerializer(serializers.ModelSerializer):
    discount_code = serializers.CharField(source="discount.code", read_only=True)
    promotion_code_value = serializers.CharField(source="promotion_code.code", read_only=True, allow_null=True)

    class Meta:
        model = DiscountRedemption
        fields = ["id", "discount", "discount_code", "promotion_code", "promotion_code_value", "customer", "subscription", "price", "original_amount_cents", "discount_amount_cents", "final_amount_cents", "metadata", "redeemed_by", "redeemed_at"]
        read_only_fields = ["id", "discount_code", "promotion_code_value", "redeemed_by", "redeemed_at"]


class RedeemDiscountSerializer(serializers.Serializer):
    organization_slug = serializers.SlugField()
    price_code = serializers.SlugField()
    promotion_code = serializers.CharField(required=False, allow_blank=True)
    discount_code = serializers.SlugField(required=False, allow_blank=True)
    idempotency_key = serializers.CharField(required=False, allow_blank=True, max_length=180)

    def validate(self, attrs):
        if not attrs.get("promotion_code") and not attrs.get("discount_code"):
            raise serializers.ValidationError("promotion_code or discount_code is required.")
        try:
            attrs["organization"] = Organization.objects.get(slug=attrs["organization_slug"], is_active=True)
        except Organization.DoesNotExist as exc:
            raise serializers.ValidationError({"organization_slug": "Organization not found."}) from exc
        try:
            attrs["price"] = Price.objects.select_related("plan", "plan__project").get(code=attrs["price_code"], is_active=True, plan__is_active=True)
        except Price.DoesNotExist as exc:
            raise serializers.ValidationError({"price_code": "Active price not found."}) from exc
        return attrs


class AddOnEntitlementSerializer(serializers.ModelSerializer):
    value = serializers.SerializerMethodField()

    class Meta:
        model = AddOnEntitlement
        fields = ["id", "addon", "key", "value_type", "bool_value", "int_value", "str_value", "value", "is_incremental", "metadata", "created_at", "updated_at"]
        read_only_fields = ["id", "value", "created_at", "updated_at"]

    def get_value(self, obj):
        return obj.value


class AddOnSerializer(serializers.ModelSerializer):
    entitlements = AddOnEntitlementSerializer(many=True, read_only=True)

    class Meta:
        model = AddOn
        fields = ["id", "project", "code", "name", "description", "billing_mode", "currency", "unit_amount_cents", "provider_price_id", "is_active", "metadata", "entitlements", "created_at", "updated_at"]
        read_only_fields = ["id", "entitlements", "created_at", "updated_at"]


class SubscriptionAddOnSerializer(serializers.ModelSerializer):
    addon_code = serializers.CharField(source="addon.code", read_only=True)

    class Meta:
        model = SubscriptionAddOn
        fields = ["id", "subscription", "addon", "addon_code", "status", "quantity", "unit_amount_cents", "provider", "provider_subscription_item_id", "current_period_end", "metadata", "created_at", "updated_at"]
        read_only_fields = ["id", "addon_code", "provider", "provider_subscription_item_id", "created_at", "updated_at"]


class AttachSubscriptionAddOnSerializer(serializers.Serializer):
    subscription = serializers.PrimaryKeyRelatedField(queryset=Subscription.objects.all())
    addon = serializers.PrimaryKeyRelatedField(queryset=AddOn.objects.filter(is_active=True))
    quantity = serializers.IntegerField(min_value=1, default=1)
    unit_amount_cents = serializers.IntegerField(min_value=0, required=False)
    current_period_end = serializers.DateTimeField(required=False, allow_null=True)
    metadata = serializers.JSONField(required=False)


class EntitlementSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = EntitlementSnapshot
        fields = ["id", "customer", "payload", "version", "calculated_at", "invalidated_at", "reason"]
        read_only_fields = ["id", "payload", "version", "calculated_at", "invalidated_at"]


class RecalculateEntitlementSnapshotSerializer(serializers.Serializer):
    customer = serializers.PrimaryKeyRelatedField(queryset=BillingCustomer.objects.all())
    reason = serializers.CharField(required=False, allow_blank=True, max_length=180)


class BillingOutboxEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = BillingOutboxEvent
        fields = [
            "id", "event_type", "aggregate_type", "aggregate_id", "status", "payload", "headers",
            "idempotency_key", "attempts", "max_attempts", "next_attempt_at", "locked_at",
            "dispatched_at", "last_error", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "attempts", "locked_at", "dispatched_at", "last_error", "created_at", "updated_at"]


class ProviderSyncStateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProviderSyncState
        fields = [
            "id", "provider", "resource_type", "cursor", "status", "last_started_at", "last_success_at",
            "last_failure_at", "last_error", "error_count", "lag_seconds", "metadata", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "last_started_at", "last_success_at", "last_failure_at", "last_error", "error_count", "created_at", "updated_at"]


class WebhookReplayRequestSerializer(serializers.ModelSerializer):
    provider = serializers.CharField(source="webhook_event.provider", read_only=True)
    event_type = serializers.CharField(source="webhook_event.event_type", read_only=True)
    event_id = serializers.CharField(source="webhook_event.event_id", read_only=True)

    class Meta:
        model = WebhookReplayRequest
        fields = [
            "id", "webhook_event", "provider", "event_type", "event_id", "status", "requested_by",
            "reason", "replayed_at", "error", "metadata", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "provider", "event_type", "event_id", "status", "requested_by", "replayed_at", "error", "created_at", "updated_at"]


class CreateWebhookReplayRequestSerializer(serializers.Serializer):
    webhook_event = serializers.PrimaryKeyRelatedField(queryset=BillingWebhookEvent.objects.all())
    reason = serializers.CharField(required=False, allow_blank=True)
    process_now = serializers.BooleanField(default=False)


class EntitlementChangeLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = EntitlementChangeLog
        fields = [
            "id", "customer", "snapshot", "previous_payload", "new_payload", "reason", "changed_by", "metadata", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class DispatchOutboxSerializer(serializers.Serializer):
    limit = serializers.IntegerField(min_value=1, max_value=500, default=50)
    event_type = serializers.CharField(required=False, allow_blank=True)
