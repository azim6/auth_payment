from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from admin_integration.permissions import (
    ADMIN_SERVICE_AUTHENTICATION_CLASSES,
    StaffOrAdminServiceScope,
    request_actor_user,
    request_admin_audit_metadata,
)
from accounts.models import Organization
from .models import (
    BillingCustomer, BillingProfile, BillingWebhookEvent, CheckoutSession, CreditNote,
    CustomerPortalSession, CustomerTaxId, DunningCase, Entitlement, Invoice,
    PaymentTransaction, Plan, Price, Project, RefundRequest, Subscription,
    SubscriptionChangeRequest, UsageMetric, UsageRecord, Discount, PromotionCode, DiscountRedemption,
    AddOn, AddOnEntitlement, SubscriptionAddOn, EntitlementSnapshot, BillingOutboxEvent, ProviderSyncState, WebhookReplayRequest, EntitlementChangeLog,
)
from .serializers import (
    BillingCustomerSerializer,
    BillingWebhookEventSerializer,
    CheckoutSessionSerializer,
    CreateCheckoutSessionSerializer,
    CreateCustomerPortalSessionSerializer,
    CustomerPortalSessionSerializer,
    CustomerEntitlementsSerializer,
    EntitlementSerializer,
    InvoiceSerializer,
    ManualSubscriptionGrantSerializer,
    PaymentTransactionSerializer,
    PlanSerializer,
    PriceSerializer,
    ProjectSerializer,
    SubscriptionSerializer,
    SubscriptionChangeRequestSerializer,
    UsageMetricSerializer,
    UsageRecordSerializer,
    RecordUsageSerializer,
    BillingProfileSerializer,
    CustomerTaxIdSerializer,
    CreditNoteSerializer,
    CreateCreditNoteSerializer,
    RefundRequestSerializer,
    ReviewRefundSerializer,
    DunningCaseSerializer,
    DiscountSerializer, PromotionCodeSerializer, DiscountRedemptionSerializer, RedeemDiscountSerializer,
    AddOnSerializer, AddOnEntitlementSerializer, SubscriptionAddOnSerializer, AttachSubscriptionAddOnSerializer,
    EntitlementSnapshotSerializer, RecalculateEntitlementSnapshotSerializer, BillingOutboxEventSerializer, ProviderSyncStateSerializer, WebhookReplayRequestSerializer, CreateWebhookReplayRequestSerializer, EntitlementChangeLogSerializer, DispatchOutboxSerializer,
)
from .services import build_customer_entitlements, can_manage_billing, get_or_create_org_customer, apply_subscription_change, record_usage, issue_credit_note, review_refund_request, redeem_discount, attach_subscription_addon, recalculate_entitlement_snapshot, build_customer_entitlements_with_addons, dispatch_due_outbox_events, create_webhook_replay_request, recalculate_entitlement_snapshot_with_log
from .payment_providers import BillingProviderError, get_billing_provider
from .webhooks import process_stripe_event


class StaffOnlyMixin:
    permission_classes = [permissions.IsAdminUser]


class ProjectListCreateView(StaffOnlyMixin, generics.ListCreateAPIView):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer


class ProjectDetailView(StaffOnlyMixin, generics.RetrieveUpdateAPIView):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    lookup_field = "code"


class PlanListCreateView(StaffOnlyMixin, generics.ListCreateAPIView):
    queryset = Plan.objects.select_related("project", "created_by").prefetch_related("prices", "entitlements")
    serializer_class = PlanSerializer


class PlanDetailView(StaffOnlyMixin, generics.RetrieveUpdateAPIView):
    queryset = Plan.objects.select_related("project", "created_by").prefetch_related("prices", "entitlements")
    serializer_class = PlanSerializer
    lookup_field = "code"


class PublicPlanListView(generics.ListAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = PlanSerializer

    def get_queryset(self):
        qs = Plan.objects.filter(is_active=True, visibility=Plan.Visibility.PUBLIC).select_related("project").prefetch_related("prices", "entitlements")
        project = self.request.query_params.get("project")
        if project:
            qs = qs.filter(project__code=project)
        return qs


class PriceListCreateView(StaffOnlyMixin, generics.ListCreateAPIView):
    queryset = Price.objects.select_related("plan")
    serializer_class = PriceSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class EntitlementListCreateView(StaffOnlyMixin, generics.ListCreateAPIView):
    queryset = Entitlement.objects.select_related("plan", "subscription")
    serializer_class = EntitlementSerializer


class BillingCustomerListView(StaffOnlyMixin, generics.ListAPIView):
    queryset = BillingCustomer.objects.select_related("organization", "user")
    serializer_class = BillingCustomerSerializer


class SubscriptionListView(StaffOnlyMixin, generics.ListAPIView):
    queryset = Subscription.objects.select_related("customer", "plan", "price", "plan__project").prefetch_related("entitlements", "plan__entitlements")
    serializer_class = SubscriptionSerializer


class ManualSubscriptionGrantView(StaffOnlyMixin, APIView):
    def post(self, request):
        serializer = ManualSubscriptionGrantSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        subscription = serializer.save()
        return Response(SubscriptionSerializer(subscription).data, status=status.HTTP_201_CREATED)


class OrganizationBillingSummaryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, slug):
        organization = get_object_or_404(Organization, slug=slug, is_active=True)
        if not can_manage_billing(request.user, organization):
            return Response({"detail": "You do not have billing access for this organization."}, status=status.HTTP_403_FORBIDDEN)
        customer = get_or_create_org_customer(organization, actor=request.user)
        subscriptions = customer.subscriptions.select_related("plan", "price", "plan__project").prefetch_related("entitlements", "plan__entitlements")
        invoices = customer.invoices.order_by("-created_at")[:10]
        return Response({
            "customer": BillingCustomerSerializer(customer).data,
            "subscriptions": SubscriptionSerializer(subscriptions, many=True).data,
            "entitlements": build_customer_entitlements(customer),
            "recent_invoices": InvoiceSerializer(invoices, many=True).data,
        })


class OrganizationEntitlementsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, slug):
        organization = get_object_or_404(Organization, slug=slug, is_active=True)
        customer = get_or_create_org_customer(organization, actor=request.user)
        return Response(build_customer_entitlements(customer))


class InvoiceListView(StaffOnlyMixin, generics.ListAPIView):
    queryset = Invoice.objects.select_related("customer", "subscription")
    serializer_class = InvoiceSerializer


class PaymentTransactionListView(StaffOnlyMixin, generics.ListAPIView):
    queryset = PaymentTransaction.objects.select_related("customer", "invoice")
    serializer_class = PaymentTransactionSerializer


class BillingWebhookEventListView(StaffOnlyMixin, generics.ListAPIView):
    queryset = BillingWebhookEvent.objects.all()
    serializer_class = BillingWebhookEventSerializer


class CheckoutSessionListView(StaffOnlyMixin, generics.ListAPIView):
    queryset = CheckoutSession.objects.select_related("customer", "plan", "price", "created_by")
    serializer_class = CheckoutSessionSerializer


class CreateCheckoutSessionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = CreateCheckoutSessionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        organization = serializer.validated_data["organization"]
        price = serializer.validated_data["price"]
        if not can_manage_billing(request.user, organization):
            return Response({"detail": "You do not have billing access for this organization."}, status=status.HTTP_403_FORBIDDEN)
        customer = get_or_create_org_customer(organization, actor=request.user)
        provider = get_billing_provider("stripe")
        try:
            provider_session = provider.create_checkout_session(
                customer=customer,
                price=price,
                success_url=serializer.validated_data["success_url"],
                cancel_url=serializer.validated_data["cancel_url"],
                metadata={
                    "organization_id": str(organization.id),
                    "billing_customer_id": str(customer.id),
                    "plan_id": str(price.plan_id),
                    "price_id": str(price.id),
                },
            )
        except BillingProviderError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        checkout = CheckoutSession.objects.create(
            customer=customer,
            plan=price.plan,
            price=price,
            provider="stripe",
            provider_session_id=provider_session.provider_session_id,
            checkout_url=provider_session.url,
            success_url=serializer.validated_data["success_url"],
            cancel_url=serializer.validated_data["cancel_url"],
            status=CheckoutSession.Status.OPEN,
            metadata=provider_session.raw or {},
            created_by=request.user,
            expires_at=provider_session.expires_at,
        )
        return Response(CheckoutSessionSerializer(checkout).data, status=status.HTTP_201_CREATED)


class CustomerPortalSessionListView(StaffOnlyMixin, generics.ListAPIView):
    queryset = CustomerPortalSession.objects.select_related("customer", "created_by")
    serializer_class = CustomerPortalSessionSerializer


class CreateCustomerPortalSessionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = CreateCustomerPortalSessionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        organization = serializer.validated_data["organization"]
        if not can_manage_billing(request.user, organization):
            return Response({"detail": "You do not have billing access for this organization."}, status=status.HTTP_403_FORBIDDEN)
        customer = get_or_create_org_customer(organization, actor=request.user)
        provider = get_billing_provider("stripe")
        try:
            provider_session = provider.create_portal_session(customer=customer, return_url=serializer.validated_data["return_url"])
        except BillingProviderError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        portal = CustomerPortalSession.objects.create(
            customer=customer,
            provider="stripe",
            provider_session_id=provider_session.provider_session_id,
            portal_url=provider_session.url,
            return_url=serializer.validated_data["return_url"],
            created_by=request.user,
        )
        return Response(CustomerPortalSessionSerializer(portal).data, status=status.HTTP_201_CREATED)


class StripeWebhookView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        signature = request.headers.get("Stripe-Signature", "")
        provider = get_billing_provider("stripe")
        try:
            event = provider.verify_webhook(request.body, signature)
        except BillingProviderError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except Exception as exc:
            BillingWebhookEvent.objects.create(
                provider="stripe",
                event_id="invalid-signature",
                event_type="invalid",
                status=BillingWebhookEvent.Status.FAILED,
                payload={"error": str(exc)},
                signature_valid=False,
                error=str(exc),
            )
            return Response({"detail": "Invalid webhook signature."}, status=status.HTTP_400_BAD_REQUEST)
        webhook = process_stripe_event(dict(event), signature_valid=True)
        return Response({"status": webhook.status, "event_id": webhook.event_id})


class SubscriptionChangeRequestListCreateView(StaffOnlyMixin, generics.ListCreateAPIView):
    queryset = SubscriptionChangeRequest.objects.select_related("subscription", "target_plan", "target_price", "requested_by")
    serializer_class = SubscriptionChangeRequestSerializer

    def perform_create(self, serializer):
        serializer.save(requested_by=self.request.user)


class ApplySubscriptionChangeView(StaffOnlyMixin, APIView):
    def post(self, request, pk):
        change = get_object_or_404(SubscriptionChangeRequest, pk=pk)
        try:
            subscription = apply_subscription_change(change)
        except Exception as exc:
            change.status = SubscriptionChangeRequest.Status.FAILED
            change.error = str(exc)
            change.save(update_fields=["status", "error", "updated_at"])
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(SubscriptionSerializer(subscription).data)


class UsageMetricListCreateView(StaffOnlyMixin, generics.ListCreateAPIView):
    queryset = UsageMetric.objects.select_related("project")
    serializer_class = UsageMetricSerializer


class UsageRecordListView(StaffOnlyMixin, generics.ListAPIView):
    queryset = UsageRecord.objects.select_related("customer", "metric")
    serializer_class = UsageRecordSerializer


class RecordUsageView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = RecordUsageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        organization = serializer.validated_data["organization"]
        if not can_manage_billing(request.user, organization) and not request.user.is_staff:
            return Response({"detail": "You do not have permission to record usage for this organization."}, status=status.HTTP_403_FORBIDDEN)
        customer = get_or_create_org_customer(organization, actor=request.user)
        usage = record_usage(
            customer=customer,
            metric=serializer.validated_data["metric"],
            quantity=serializer.validated_data["quantity"],
            idempotency_key=serializer.validated_data.get("idempotency_key", ""),
            source=serializer.validated_data.get("source", "api"),
            metadata=serializer.validated_data.get("metadata", {}),
        )
        return Response(UsageRecordSerializer(usage).data, status=status.HTTP_201_CREATED)


class OrganizationUsageSummaryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, slug):
        organization = get_object_or_404(Organization, slug=slug, is_active=True)
        if not can_manage_billing(request.user, organization):
            return Response({"detail": "You do not have billing access for this organization."}, status=status.HTTP_403_FORBIDDEN)
        customer = get_or_create_org_customer(organization, actor=request.user)
        entitlements = build_customer_entitlements(customer).get("features", {})
        metrics = UsageMetric.objects.filter(is_active=True).select_related("project")
        rows = []
        now = __import__("django.utils.timezone", fromlist=["now"]).now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        for metric in metrics:
            from .services import usage_total_for_period
            used = usage_total_for_period(customer=customer, metric=metric, start=month_start, end=now)
            limit = entitlements.get(metric.entitlement_key)
            rows.append({
                "metric": metric.code,
                "project": metric.project.code if metric.project_id else "global",
                "used_this_month": used,
                "limit": limit,
                "remaining": max(limit - used, 0) if isinstance(limit, int) else None,
                "unit": metric.unit,
            })
        return Response({"customer_id": str(customer.id), "month_start": month_start, "usage": rows})


class BillingProfileListCreateView(StaffOnlyMixin, generics.ListCreateAPIView):
    queryset = BillingProfile.objects.select_related("customer", "customer__organization", "customer__user")
    serializer_class = BillingProfileSerializer


class CustomerTaxIdListCreateView(StaffOnlyMixin, generics.ListCreateAPIView):
    queryset = CustomerTaxId.objects.select_related("customer", "customer__organization", "customer__user")
    serializer_class = CustomerTaxIdSerializer


class CreditNoteListView(StaffOnlyMixin, generics.ListAPIView):
    queryset = CreditNote.objects.select_related("customer", "invoice", "issued_by")
    serializer_class = CreditNoteSerializer


class IssueCreditNoteView(StaffOnlyMixin, APIView):
    def post(self, request):
        serializer = CreateCreditNoteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        credit = issue_credit_note(
            customer=serializer.validated_data["customer"],
            invoice=serializer.validated_data.get("invoice"),
            reason=serializer.validated_data.get("reason"),
            currency=serializer.validated_data.get("currency", "USD"),
            amount_cents=serializer.validated_data["amount_cents"],
            memo=serializer.validated_data.get("memo", ""),
            metadata=serializer.validated_data.get("metadata", {}),
            actor=request.user,
        )
        return Response(CreditNoteSerializer(credit).data, status=status.HTTP_201_CREATED)


class RefundRequestListCreateView(StaffOnlyMixin, generics.ListCreateAPIView):
    queryset = RefundRequest.objects.select_related("customer", "payment", "invoice", "credit_note", "requested_by", "reviewed_by")
    serializer_class = RefundRequestSerializer

    def perform_create(self, serializer):
        serializer.save(requested_by=self.request.user)


class ReviewRefundRequestView(StaffOnlyMixin, APIView):
    def post(self, request, pk):
        refund = get_object_or_404(RefundRequest, pk=pk)
        serializer = ReviewRefundSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            refund = review_refund_request(
                refund=refund,
                actor=request.user,
                action=serializer.validated_data["action"],
                note=serializer.validated_data.get("note", ""),
                provider_refund_id=serializer.validated_data.get("provider_refund_id", ""),
            )
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(RefundRequestSerializer(refund).data)


class DunningCaseListCreateView(StaffOnlyMixin, generics.ListCreateAPIView):
    queryset = DunningCase.objects.select_related("customer", "subscription", "invoice")
    serializer_class = DunningCaseSerializer


class DiscountListCreateView(StaffOnlyMixin, generics.ListCreateAPIView):
    queryset = Discount.objects.prefetch_related("applies_to_projects", "applies_to_plans")
    serializer_class = DiscountSerializer


class PromotionCodeListCreateView(StaffOnlyMixin, generics.ListCreateAPIView):
    queryset = PromotionCode.objects.select_related("discount", "organization")
    serializer_class = PromotionCodeSerializer


class DiscountRedemptionListView(StaffOnlyMixin, generics.ListAPIView):
    queryset = DiscountRedemption.objects.select_related("discount", "promotion_code", "customer", "subscription", "price", "redeemed_by")
    serializer_class = DiscountRedemptionSerializer


class RedeemDiscountView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = RedeemDiscountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        organization = serializer.validated_data["organization"]
        if not can_manage_billing(request.user, organization):
            return Response({"detail": "You do not have billing access for this organization."}, status=status.HTTP_403_FORBIDDEN)
        customer = get_or_create_org_customer(organization, actor=request.user)
        try:
            redemption = redeem_discount(
                customer=customer,
                price=serializer.validated_data["price"],
                promotion_code=serializer.validated_data.get("promotion_code", ""),
                discount_code=serializer.validated_data.get("discount_code", ""),
                idempotency_key=serializer.validated_data.get("idempotency_key", ""),
                actor=request.user,
            )
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(DiscountRedemptionSerializer(redemption).data, status=status.HTTP_201_CREATED)


class AddOnListCreateView(StaffOnlyMixin, generics.ListCreateAPIView):
    queryset = AddOn.objects.select_related("project").prefetch_related("entitlements")
    serializer_class = AddOnSerializer


class AddOnEntitlementListCreateView(StaffOnlyMixin, generics.ListCreateAPIView):
    queryset = AddOnEntitlement.objects.select_related("addon")
    serializer_class = AddOnEntitlementSerializer


class SubscriptionAddOnListView(StaffOnlyMixin, generics.ListAPIView):
    queryset = SubscriptionAddOn.objects.select_related("subscription", "addon", "created_by")
    serializer_class = SubscriptionAddOnSerializer


class AttachSubscriptionAddOnView(StaffOnlyMixin, APIView):
    def post(self, request):
        serializer = AttachSubscriptionAddOnSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        addon = attach_subscription_addon(
            subscription=serializer.validated_data["subscription"],
            addon=serializer.validated_data["addon"],
            quantity=serializer.validated_data.get("quantity", 1),
            unit_amount_cents=serializer.validated_data.get("unit_amount_cents"),
            current_period_end=serializer.validated_data.get("current_period_end"),
            metadata=serializer.validated_data.get("metadata", {}),
            actor=request.user,
        )
        return Response(SubscriptionAddOnSerializer(addon).data, status=status.HTTP_201_CREATED)


class EntitlementSnapshotListView(StaffOnlyMixin, generics.ListAPIView):
    queryset = EntitlementSnapshot.objects.select_related("customer", "customer__organization", "customer__user")
    serializer_class = EntitlementSnapshotSerializer


class RecalculateEntitlementSnapshotView(StaffOnlyMixin, APIView):
    def post(self, request):
        serializer = RecalculateEntitlementSnapshotSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        snapshot = recalculate_entitlement_snapshot(
            customer=serializer.validated_data["customer"],
            reason=serializer.validated_data.get("reason", "manual"),
        )
        return Response(EntitlementSnapshotSerializer(snapshot).data)


class OrganizationEntitlementSnapshotView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, slug):
        organization = get_object_or_404(Organization, slug=slug, is_active=True)
        customer = get_or_create_org_customer(organization, actor=request.user)
        snapshot = EntitlementSnapshot.objects.filter(customer=customer, invalidated_at__isnull=True).first()
        if not snapshot:
            snapshot = recalculate_entitlement_snapshot(customer=customer, reason="api_read")
        return Response(EntitlementSnapshotSerializer(snapshot).data)


class BillingOutboxEventListCreateView(StaffOnlyMixin, generics.ListCreateAPIView):
    queryset = BillingOutboxEvent.objects.all()
    serializer_class = BillingOutboxEventSerializer


class DispatchBillingOutboxView(StaffOnlyMixin, APIView):
    def post(self, request):
        serializer = DispatchOutboxSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = dispatch_due_outbox_events(
            limit=serializer.validated_data["limit"],
            event_type=serializer.validated_data.get("event_type", ""),
        )
        return Response(result)


class ProviderSyncStateListCreateView(StaffOnlyMixin, generics.ListCreateAPIView):
    queryset = ProviderSyncState.objects.all()
    serializer_class = ProviderSyncStateSerializer


class WebhookReplayRequestListView(StaffOnlyMixin, generics.ListAPIView):
    queryset = WebhookReplayRequest.objects.select_related("webhook_event", "requested_by")
    serializer_class = WebhookReplayRequestSerializer


class CreateWebhookReplayRequestView(StaffOnlyMixin, APIView):
    def post(self, request):
        serializer = CreateWebhookReplayRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        replay = create_webhook_replay_request(
            webhook_event=serializer.validated_data["webhook_event"],
            actor=request.user,
            reason=serializer.validated_data.get("reason", ""),
            process_now=serializer.validated_data.get("process_now", False),
        )
        return Response(WebhookReplayRequestSerializer(replay).data, status=status.HTTP_201_CREATED)


class EntitlementChangeLogListView(StaffOnlyMixin, generics.ListAPIView):
    queryset = EntitlementChangeLog.objects.select_related("customer", "snapshot", "changed_by")
    serializer_class = EntitlementChangeLogSerializer


class RecalculateEntitlementSnapshotWithLogView(StaffOnlyMixin, APIView):
    authentication_classes = ADMIN_SERVICE_AUTHENTICATION_CLASSES
    permission_classes = [StaffOrAdminServiceScope]
    required_admin_scopes = ["admin:entitlements:write"]

    def post(self, request):
        serializer = RecalculateEntitlementSnapshotSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        snapshot = recalculate_entitlement_snapshot_with_log(
            customer=serializer.validated_data["customer"],
            reason=serializer.validated_data.get("reason", "manual"),
            actor=request_actor_user(request),
            metadata=request_admin_audit_metadata(request),
        )
        return Response(EntitlementSnapshotSerializer(snapshot).data)


class BillingReadinessView(StaffOnlyMixin, APIView):
    """Staff-only production readiness check for the billing/payment subsystem."""
    authentication_classes = ADMIN_SERVICE_AUTHENTICATION_CLASSES
    permission_classes = [StaffOrAdminServiceScope]
    required_admin_scopes = ["admin:readiness"]

    def get(self, request):
        from datetime import timedelta
        from django.utils import timezone as django_timezone

        missing_settings = []
        for name in ["STRIPE_SECRET_KEY", "STRIPE_WEBHOOK_SECRET"]:
            if not getattr(settings, name, ""):
                missing_settings.append(name)
        active_stripe_prices = Price.objects.filter(is_active=True, provider_price_id__gt="").count()
        active_prices_missing_provider = Price.objects.filter(is_active=True, amount_cents__gt=0, provider_price_id="").count()
        recent_failed_webhooks = BillingWebhookEvent.objects.filter(
            status=BillingWebhookEvent.Status.FAILED,
            created_at__gte=django_timezone.now() - timedelta(hours=24),
        ).count()
        provider_states = list(ProviderSyncState.objects.values("provider", "resource_type", "status", "last_error", "lag_seconds"))
        return Response({
            "ready": not missing_settings and active_prices_missing_provider == 0,
            "missing_settings": missing_settings,
            "active_stripe_prices": active_stripe_prices,
            "active_prices_missing_provider": active_prices_missing_provider,
            "failed_webhooks_24h": recent_failed_webhooks,
            "provider_sync_states": provider_states,
            "recommended_next_checks": [
                "Run Stripe CLI webhook replay against /api/v1/billing/webhooks/stripe/.",
                "Create one test checkout session for each public paid plan.",
                "Verify entitlement snapshots after subscription.updated and invoice.payment_failed events.",
            ],
        })
