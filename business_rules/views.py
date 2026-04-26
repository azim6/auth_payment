from rest_framework import generics, permissions, response, views, viewsets
from rest_framework.decorators import action

from .catalog import BUSINESS_PRODUCTS
from .models import ProductAccessDecision, ProductAccessOverride, ProductUsageEvent
from .serializers import (
    AccessCheckSerializer,
    ProductAccessDecisionSerializer,
    ProductAccessOverrideSerializer,
    ProductAccessSummarySerializer,
    ProductUsageEventSerializer,
)


class StaffOnlyMixin:
    permission_classes = [permissions.IsAdminUser]


class ProductCatalogView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return response.Response({"products": BUSINESS_PRODUCTS})


class AccessCheckView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = AccessCheckSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        return response.Response(serializer.save())


class ProductAccessSummaryView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ProductAccessSummarySerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        return response.Response(serializer.save())


class ProductAccessOverrideViewSet(StaffOnlyMixin, viewsets.ModelViewSet):
    serializer_class = ProductAccessOverrideSerializer
    queryset = ProductAccessOverride.objects.select_related("user", "organization", "created_by")

    @action(detail=True, methods=["post"])
    def deactivate(self, request, pk=None):
        override = self.get_object()
        override.is_active = False
        override.save(update_fields=["is_active", "updated_at"])
        return response.Response(ProductAccessOverrideSerializer(override, context={"request": request}).data)


class ProductUsageEventListView(StaffOnlyMixin, generics.ListAPIView):
    serializer_class = ProductUsageEventSerializer
    queryset = ProductUsageEvent.objects.select_related("user", "organization")

    def get_queryset(self):
        qs = super().get_queryset()
        product = self.request.query_params.get("product")
        action = self.request.query_params.get("action")
        if product:
            qs = qs.filter(product=product)
        if action:
            qs = qs.filter(action=action)
        return qs


class ProductAccessDecisionListView(StaffOnlyMixin, generics.ListAPIView):
    serializer_class = ProductAccessDecisionSerializer
    queryset = ProductAccessDecision.objects.select_related("user", "organization")

    def get_queryset(self):
        qs = super().get_queryset()
        product = self.request.query_params.get("product")
        allowed = self.request.query_params.get("allowed")
        if product:
            qs = qs.filter(product=product)
        if allowed in {"true", "false"}:
            qs = qs.filter(allowed=allowed == "true")
        return qs


class ResetUsageView(StaffOnlyMixin, views.APIView):
    def post(self, request):
        user_id = request.data.get("user_id")
        organization_id = request.data.get("organization_id")
        organization_slug = request.data.get("organization_slug")
        product = request.data.get("product")
        action = request.data.get("action")
        period_key = request.data.get("period_key")
        qs = ProductUsageEvent.objects.all()
        if user_id:
            qs = qs.filter(user_id=user_id)
        if organization_id:
            qs = qs.filter(organization_id=organization_id)
        if organization_slug:
            qs = qs.filter(organization__slug=organization_slug)
        if product:
            qs = qs.filter(product=product)
        if action:
            qs = qs.filter(action=action)
        if period_key:
            qs = qs.filter(period_key=period_key)
        deleted, _ = qs.delete()
        return response.Response({"deleted_usage_events": deleted})
