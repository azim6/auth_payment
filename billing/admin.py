from django.contrib import admin

from .models import BillingCustomer, BillingProfile, BillingWebhookEvent, CheckoutSession, CreditNote, CustomerPortalSession, CustomerTaxId, DunningCase, Entitlement, Invoice, PaymentTransaction, Plan, Price, Project, RefundRequest, Subscription, SubscriptionChangeRequest, UsageMetric, UsageRecord, Discount, PromotionCode, DiscountRedemption, AddOn, AddOnEntitlement, SubscriptionAddOn, EntitlementSnapshot, BillingOutboxEvent, ProviderSyncState, WebhookReplayRequest, EntitlementChangeLog


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_active", "created_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("code", "name")
    readonly_fields = ("id", "created_at", "updated_at")


class PriceInline(admin.TabularInline):
    model = Price
    extra = 0
    fields = ("code", "currency", "amount_cents", "interval", "is_active", "is_custom", "provider_price_id")


class EntitlementInline(admin.TabularInline):
    model = Entitlement
    extra = 0
    fields = ("key", "value_type", "bool_value", "int_value", "str_value")


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "project", "visibility", "is_active", "trial_days", "created_at")
    list_filter = ("visibility", "is_active", "project", "created_at")
    search_fields = ("code", "name", "project__code")
    readonly_fields = ("id", "created_at", "updated_at")
    inlines = [PriceInline, EntitlementInline]


@admin.register(Price)
class PriceAdmin(admin.ModelAdmin):
    list_display = ("code", "plan", "currency", "amount_cents", "interval", "is_custom", "is_active")
    list_filter = ("currency", "interval", "is_custom", "is_active")
    search_fields = ("code", "plan__code", "provider_price_id")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(BillingCustomer)
class BillingCustomerAdmin(admin.ModelAdmin):
    list_display = ("id", "organization", "user", "billing_email", "provider", "provider_customer_id", "created_at")
    list_filter = ("provider", "created_at")
    search_fields = ("organization__slug", "user__email", "billing_email", "provider_customer_id")
    readonly_fields = ("id", "created_at", "updated_at")


class SubscriptionEntitlementInline(admin.TabularInline):
    model = Entitlement
    extra = 0
    fields = ("key", "value_type", "bool_value", "int_value", "str_value")


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "plan", "status", "provider", "current_period_end", "cancel_at_period_end", "created_at")
    list_filter = ("status", "provider", "cancel_at_period_end", "created_at")
    search_fields = ("customer__organization__slug", "customer__user__email", "plan__code", "provider_subscription_id")
    readonly_fields = ("id", "created_at", "updated_at")
    inlines = [SubscriptionEntitlementInline]


@admin.register(Entitlement)
class EntitlementAdmin(admin.ModelAdmin):
    list_display = ("key", "plan", "subscription", "value_type", "bool_value", "int_value", "str_value")
    list_filter = ("value_type",)
    search_fields = ("key", "plan__code")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "status", "currency", "amount_due_cents", "amount_paid_cents", "provider", "created_at")
    list_filter = ("status", "provider", "currency", "created_at")
    search_fields = ("provider_invoice_id", "customer__organization__slug", "customer__user__email")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "status", "currency", "amount_cents", "provider", "created_at")
    list_filter = ("status", "provider", "currency", "created_at")
    search_fields = ("provider_payment_id", "customer__organization__slug", "customer__user__email")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(BillingWebhookEvent)
class BillingWebhookEventAdmin(admin.ModelAdmin):
    list_display = ("provider", "event_id", "event_type", "status", "signature_valid", "created_at", "processed_at")
    list_filter = ("provider", "event_type", "status", "signature_valid", "created_at")
    search_fields = ("event_id", "event_type")
    readonly_fields = ("id", "provider", "event_id", "event_type", "status", "payload", "signature_valid", "processed_at", "error", "created_at")


@admin.register(CheckoutSession)
class CheckoutSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "plan", "price", "provider", "status", "created_by", "created_at")
    list_filter = ("provider", "status", "created_at")
    search_fields = ("provider_session_id", "customer__organization__slug", "customer__user__email", "plan__code", "price__code")
    readonly_fields = ("id", "provider_session_id", "checkout_url", "metadata", "created_at", "updated_at", "completed_at")


@admin.register(CustomerPortalSession)
class CustomerPortalSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "provider", "created_by", "created_at")
    list_filter = ("provider", "created_at")
    search_fields = ("provider_session_id", "customer__organization__slug", "customer__user__email")
    readonly_fields = ("id", "provider_session_id", "portal_url", "created_at")


@admin.register(SubscriptionChangeRequest)
class SubscriptionChangeRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "subscription", "action", "status", "effective_at", "requested_by", "created_at")
    list_filter = ("action", "status", "provider", "created_at")
    search_fields = ("subscription__provider_subscription_id", "subscription__customer__organization__slug", "reason")
    readonly_fields = ("id", "applied_at", "provider_change_id", "error", "created_at", "updated_at")


@admin.register(UsageMetric)
class UsageMetricAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "project", "unit", "aggregation", "entitlement_key", "is_active")
    list_filter = ("aggregation", "is_active", "project")
    search_fields = ("code", "name", "entitlement_key")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(UsageRecord)
class UsageRecordAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "metric", "quantity", "source", "occurred_at", "created_at")
    list_filter = ("source", "metric", "occurred_at", "created_at")
    search_fields = ("customer__organization__slug", "customer__user__email", "metric__code", "idempotency_key")
    readonly_fields = ("id", "created_at")


@admin.register(BillingProfile)
class BillingProfileAdmin(admin.ModelAdmin):
    list_display = ("customer", "legal_name", "billing_email", "country", "tax_exempt_status", "default_currency")
    list_filter = ("country", "tax_exempt_status", "default_currency")
    search_fields = ("customer__organization__slug", "customer__user__email", "legal_name", "billing_email")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(CustomerTaxId)
class CustomerTaxIdAdmin(admin.ModelAdmin):
    list_display = ("customer", "tax_type", "country", "status", "provider", "is_default", "created_at")
    list_filter = ("tax_type", "country", "status", "provider", "is_default")
    search_fields = ("customer__organization__slug", "customer__user__email", "value", "provider_tax_id")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(CreditNote)
class CreditNoteAdmin(admin.ModelAdmin):
    list_display = ("number", "customer", "status", "reason", "currency", "amount_cents", "issued_at")
    list_filter = ("status", "reason", "currency", "provider", "created_at")
    search_fields = ("number", "provider_credit_note_id", "customer__organization__slug", "customer__user__email")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(RefundRequest)
class RefundRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "status", "currency", "amount_cents", "provider", "created_at", "processed_at")
    list_filter = ("status", "provider", "currency", "created_at")
    search_fields = ("provider_refund_id", "customer__organization__slug", "customer__user__email", "reason")
    readonly_fields = ("id", "created_at", "updated_at", "reviewed_at", "processed_at")


@admin.register(DunningCase)
class DunningCaseAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "status", "failed_attempts", "next_retry_at", "grace_ends_at", "created_at")
    list_filter = ("status", "created_at", "grace_ends_at")
    search_fields = ("customer__organization__slug", "customer__user__email", "resolution_note")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(Discount)
class DiscountAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "discount_type", "is_active", "redeemed_count", "max_redemptions", "expires_at")
    list_filter = ("discount_type", "duration", "is_active", "expires_at")
    search_fields = ("code", "name")
    readonly_fields = ("id", "redeemed_count", "created_at", "updated_at")
    filter_horizontal = ("applies_to_projects", "applies_to_plans")


@admin.register(PromotionCode)
class PromotionCodeAdmin(admin.ModelAdmin):
    list_display = ("code", "discount", "organization", "is_active", "redeemed_count", "max_redemptions", "expires_at")
    list_filter = ("is_active", "expires_at")
    search_fields = ("code", "discount__code", "organization__slug")
    readonly_fields = ("id", "redeemed_count", "created_at", "updated_at")


@admin.register(DiscountRedemption)
class DiscountRedemptionAdmin(admin.ModelAdmin):
    list_display = ("id", "discount", "promotion_code", "customer", "original_amount_cents", "discount_amount_cents", "final_amount_cents", "redeemed_at")
    list_filter = ("discount", "redeemed_at")
    search_fields = ("customer__organization__slug", "customer__user__email", "discount__code", "promotion_code__code", "idempotency_key")
    readonly_fields = ("id", "redeemed_at")


class AddOnEntitlementInline(admin.TabularInline):
    model = AddOnEntitlement
    extra = 0
    fields = ("key", "value_type", "bool_value", "int_value", "str_value", "is_incremental")


@admin.register(AddOn)
class AddOnAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "project", "billing_mode", "currency", "unit_amount_cents", "is_active")
    list_filter = ("billing_mode", "currency", "is_active", "project")
    search_fields = ("code", "name", "provider_price_id")
    readonly_fields = ("id", "created_at", "updated_at")
    inlines = [AddOnEntitlementInline]


@admin.register(AddOnEntitlement)
class AddOnEntitlementAdmin(admin.ModelAdmin):
    list_display = ("addon", "key", "value_type", "int_value", "bool_value", "is_incremental")
    list_filter = ("value_type", "is_incremental")
    search_fields = ("addon__code", "key")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(SubscriptionAddOn)
class SubscriptionAddOnAdmin(admin.ModelAdmin):
    list_display = ("subscription", "addon", "status", "quantity", "unit_amount_cents", "provider", "current_period_end")
    list_filter = ("status", "provider", "addon")
    search_fields = ("subscription__customer__organization__slug", "addon__code", "provider_subscription_item_id")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(EntitlementSnapshot)
class EntitlementSnapshotAdmin(admin.ModelAdmin):
    list_display = ("customer", "version", "calculated_at", "invalidated_at", "reason")
    list_filter = ("calculated_at", "invalidated_at")
    search_fields = ("customer__organization__slug", "customer__user__email", "reason")
    readonly_fields = ("id", "payload", "version", "calculated_at", "invalidated_at")


@admin.register(BillingOutboxEvent)
class BillingOutboxEventAdmin(admin.ModelAdmin):
    list_display = ("event_type", "aggregate_type", "aggregate_id", "status", "attempts", "next_attempt_at", "dispatched_at", "created_at")
    list_filter = ("status", "event_type", "created_at")
    search_fields = ("event_type", "aggregate_type", "aggregate_id", "idempotency_key")
    readonly_fields = ("id", "attempts", "locked_at", "dispatched_at", "last_error", "created_at", "updated_at")


@admin.register(ProviderSyncState)
class ProviderSyncStateAdmin(admin.ModelAdmin):
    list_display = ("provider", "resource_type", "status", "lag_seconds", "error_count", "last_success_at", "last_failure_at")
    list_filter = ("provider", "resource_type", "status")
    search_fields = ("provider", "resource_type", "cursor")
    readonly_fields = ("id", "last_started_at", "last_success_at", "last_failure_at", "last_error", "error_count", "created_at", "updated_at")


@admin.register(WebhookReplayRequest)
class WebhookReplayRequestAdmin(admin.ModelAdmin):
    list_display = ("webhook_event", "status", "requested_by", "replayed_at", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("webhook_event__event_id", "webhook_event__event_type", "reason", "error")
    readonly_fields = ("id", "replayed_at", "error", "created_at", "updated_at")


@admin.register(EntitlementChangeLog)
class EntitlementChangeLogAdmin(admin.ModelAdmin):
    list_display = ("customer", "snapshot", "reason", "changed_by", "created_at")
    list_filter = ("reason", "created_at")
    search_fields = ("customer__organization__slug", "customer__user__email", "reason")
    readonly_fields = ("id", "created_at")
