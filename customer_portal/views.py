from django.db.models import Count, Q
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import OrganizationMembership
from billing.models import BillingCustomer, Invoice, Subscription
from .models import PortalActivityLog, PortalApiKey, PortalOrganizationBookmark, PortalProfileSettings, PortalSupportRequest
from .serializers import (
    PortalActivityLogSerializer,
    PortalApiKeyCreateSerializer,
    PortalApiKeySerializer,
    PortalOrganizationBookmarkSerializer,
    PortalProfileSettingsSerializer,
    PortalSupportRequestSerializer,
)
from .services import build_customer_portal_readiness, build_portal_summary, escalate_support_request_to_operator_task, record_portal_activity


class IsStaffOperator(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)


class PortalReadinessView(APIView):
    permission_classes = [IsStaffOperator]

    def get(self, request):
        return Response(build_customer_portal_readiness())


class PortalSummaryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(build_portal_summary(request.user))


class PortalProfileSettingsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self, request):
        obj, _ = PortalProfileSettings.objects.get_or_create(user=request.user)
        return obj

    def get(self, request):
        return Response(PortalProfileSettingsSerializer(self.get_object(request)).data)

    def patch(self, request):
        obj = self.get_object(request)
        serializer = PortalProfileSettingsSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        record_portal_activity(
            user=request.user,
            domain=PortalActivityLog.Domain.AUTH,
            event_type="portal.profile_settings.updated",
            title="Profile settings updated",
            request=request,
        )
        return Response(serializer.data)


class PortalOrganizationViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "organization__slug"

    def get_queryset(self):
        return OrganizationMembership.objects.filter(user=self.request.user).select_related("organization")

    def list(self, request):
        memberships = self.get_queryset()
        data = [
            {
                "id": str(m.organization.id),
                "slug": m.organization.slug,
                "name": m.organization.name,
                "role": m.role,
                "is_active": m.organization.is_active,
                "joined_at": m.joined_at,
            }
            for m in memberships
        ]
        return Response(data)

    @action(detail=False, methods=["get"], url_path="(?P<slug>[-a-zA-Z0-9_]+)/overview")
    def overview(self, request, slug=None):
        membership = self.get_queryset().filter(organization__slug=slug).select_related("organization").first()
        if not membership:
            return Response({"detail": "Organization not found."}, status=status.HTTP_404_NOT_FOUND)
        org = membership.organization
        customer = BillingCustomer.objects.filter(organization=org).first()
        subscriptions = Subscription.objects.filter(customer=customer) if customer else Subscription.objects.none()
        invoices = Invoice.objects.filter(customer=customer).order_by("-created_at")[:10] if customer else []
        members = OrganizationMembership.objects.filter(organization=org).values("role").annotate(count=Count("id"))
        return Response(
            {
                "organization": {"id": str(org.id), "slug": org.slug, "name": org.name, "is_active": org.is_active},
                "membership": {"role": membership.role, "joined_at": membership.joined_at},
                "members_by_role": list(members),
                "subscriptions": [
                    {"id": str(s.id), "plan": s.plan.code, "status": s.status, "current_period_end": s.current_period_end, "seat_limit": s.seat_limit}
                    for s in subscriptions.select_related("plan")[:20]
                ],
                "recent_invoices": [
                    {"id": str(i.id), "number": str(i.id), "status": i.status, "currency": i.currency, "amount_due_cents": i.amount_due_cents, "due_at": i.due_at}
                    for i in invoices
                ],
            }
        )


class PortalOrganizationBookmarkViewSet(viewsets.ModelViewSet):
    serializer_class = PortalOrganizationBookmarkSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return PortalOrganizationBookmark.objects.filter(user=self.request.user).select_related("organization")

    def perform_create(self, serializer):
        organization = serializer.validated_data["organization"]
        if not OrganizationMembership.objects.filter(user=self.request.user, organization=organization).exists():
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You can only bookmark organizations where you are a member.")
        serializer.save(user=self.request.user)


class PortalApiKeyViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return PortalApiKey.objects.filter(user=self.request.user).select_related("organization")

    def get_serializer_class(self):
        if self.action == "create":
            return PortalApiKeyCreateSerializer
        return PortalApiKeySerializer

    @action(detail=True, methods=["post"])
    def revoke(self, request, pk=None):
        key = self.get_object()
        key.revoke()
        record_portal_activity(
            user=request.user,
            organization=key.organization,
            domain=PortalActivityLog.Domain.API,
            event_type="portal_api_key.revoked",
            title="API key revoked",
            request=request,
            summary=f"Customer portal API key '{key.name}' was revoked.",
        )
        return Response(PortalApiKeySerializer(key).data)


class PortalBillingView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        org_slugs = request.query_params.getlist("organization")
        memberships = OrganizationMembership.objects.filter(user=request.user).select_related("organization")
        if org_slugs:
            memberships = memberships.filter(organization__slug__in=org_slugs)
        orgs = [m.organization for m in memberships]
        customers = BillingCustomer.objects.filter(Q(organization__in=orgs) | Q(user=request.user)).select_related("organization", "user")
        customer_ids = list(customers.values_list("id", flat=True))
        subscriptions = Subscription.objects.filter(customer_id__in=customer_ids).select_related("plan", "price", "customer")
        invoices = Invoice.objects.filter(customer_id__in=customer_ids).order_by("-created_at")[:50]
        return Response(
            {
                "customers": [
                    {
                        "id": str(c.id),
                        "organization": c.organization.slug if c.organization else None,
                        "billing_email": c.billing_email,
                        "provider": c.provider,
                    }
                    for c in customers
                ],
                "subscriptions": [
                    {
                        "id": str(s.id),
                        "customer_id": str(s.customer_id),
                        "plan": s.plan.code,
                        "status": s.status,
                        "quantity": s.quantity,
                        "seat_limit": s.seat_limit,
                        "current_period_end": s.current_period_end,
                        "cancel_at_period_end": s.cancel_at_period_end,
                    }
                    for s in subscriptions
                ],
                "recent_invoices": [
                    {
                        "id": str(i.id),
                        "number": str(i.id),
                        "status": i.status,
                        "currency": i.currency,
                        "amount_due_cents": i.amount_due_cents,
                        "due_at": i.due_at,
                    }
                    for i in invoices
                ],
            }
        )


class PortalSupportRequestViewSet(viewsets.ModelViewSet):
    serializer_class = PortalSupportRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return PortalSupportRequest.objects.filter(user=self.request.user).select_related("organization")

    def perform_create(self, serializer):
        organization = serializer.validated_data.get("organization")
        if organization and not OrganizationMembership.objects.filter(user=self.request.user, organization=organization).exists():
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You can only create support requests for organizations where you are a member.")
        obj = serializer.save(user=self.request.user)
        record_portal_activity(
            user=self.request.user,
            organization=obj.organization,
            domain=PortalActivityLog.Domain.ORGANIZATION if obj.organization else PortalActivityLog.Domain.AUTH,
            event_type="support_request.created",
            title="Support request created",
            request=self.request,
            summary=obj.subject,
        )

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        obj = self.get_object()
        obj.status = PortalSupportRequest.Status.CLOSED
        obj.save(update_fields=["status", "updated_at"])
        return Response(PortalSupportRequestSerializer(obj).data)


    @action(detail=True, methods=["post"])
    def escalate(self, request, pk=None):
        obj = self.get_object()
        task = escalate_support_request_to_operator_task(support_request=obj, operator=request.user)
        payload = PortalSupportRequestSerializer(obj).data
        payload["operator_task_id"] = str(task.id) if task else None
        return Response(payload)


class PortalActivityLogViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = PortalActivityLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = PortalActivityLog.objects.filter(user=self.request.user).select_related("organization")
        domain = self.request.query_params.get("domain")
        if domain:
            qs = qs.filter(domain=domain)
        return qs
