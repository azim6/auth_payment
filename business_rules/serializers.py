from rest_framework import serializers

from .catalog import BUSINESS_PRODUCTS
from .models import ProductAccessDecision, ProductAccessOverride, ProductUsageEvent
from .services import check_product_access, product_access_summary, record_usage, resolve_subject


class ProductCatalogSerializer(serializers.Serializer):
    products = serializers.DictField(read_only=True)


class AccessCheckSerializer(serializers.Serializer):
    user_id = serializers.UUIDField(required=False)
    organization_slug = serializers.SlugField(required=False)
    organization_id = serializers.UUIDField(required=False)
    product = serializers.SlugField()
    action = serializers.SlugField()
    quantity = serializers.IntegerField(required=False, min_value=1, default=1)
    record_usage = serializers.BooleanField(required=False, default=False)
    idempotency_key = serializers.CharField(required=False, allow_blank=True, default="")
    source = serializers.CharField(required=False, allow_blank=True, default="api")
    metadata = serializers.DictField(required=False, default=dict)

    def validate(self, attrs):
        if not attrs.get("user_id") and not attrs.get("organization_slug") and not attrs.get("organization_id"):
            request = self.context.get("request")
            if request and request.user and request.user.is_authenticated:
                attrs["user_id"] = request.user.id
            else:
                raise serializers.ValidationError("Provide user_id, organization_slug, or organization_id.")
        return attrs

    def save(self, **kwargs):
        request = self.context.get("request")
        subject = resolve_subject(
            user_id=self.validated_data.get("user_id"),
            organization_slug=self.validated_data.get("organization_slug"),
            organization_id=self.validated_data.get("organization_id"),
            actor=getattr(request, "user", None),
        )
        decision = check_product_access(
            subject=subject,
            product=self.validated_data["product"],
            action=self.validated_data["action"],
            quantity=self.validated_data.get("quantity", 1),
        )
        if decision.get("allowed") and self.validated_data.get("record_usage"):
            event = record_usage(
                subject=subject,
                product=self.validated_data["product"],
                action=self.validated_data["action"],
                quantity=self.validated_data.get("quantity", 1),
                idempotency_key=self.validated_data.get("idempotency_key", ""),
                source=self.validated_data.get("source", "api"),
                metadata=self.validated_data.get("metadata", {}),
            )
            decision["usage_event_id"] = str(event.id)
        return decision


class ProductAccessOverrideSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductAccessOverride
        fields = [
            "id",
            "user",
            "organization",
            "product",
            "action",
            "entitlement_key",
            "effect",
            "bool_value",
            "int_value",
            "reason",
            "is_active",
            "expires_at",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]

    def validate(self, attrs):
        user = attrs.get("user", getattr(self.instance, "user", None))
        organization = attrs.get("organization", getattr(self.instance, "organization", None))
        if bool(user) == bool(organization):
            raise serializers.ValidationError("Exactly one of user or organization is required.")
        product = attrs.get("product", getattr(self.instance, "product", None))
        if product and product not in BUSINESS_PRODUCTS:
            raise serializers.ValidationError({"product": "Unknown business product."})
        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        if request and request.user and request.user.is_authenticated:
            validated_data["created_by"] = request.user
        return super().create(validated_data)


class ProductUsageEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductUsageEvent
        fields = ["id", "user", "organization", "product", "action", "quantity", "period_key", "idempotency_key", "source", "metadata", "created_at"]
        read_only_fields = ["id", "created_at"]


class ProductAccessDecisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductAccessDecision
        fields = ["id", "user", "organization", "product", "action", "allowed", "reason", "remaining", "limit", "used", "plan_codes", "metadata", "created_at"]
        read_only_fields = fields


class ProductAccessSummarySerializer(serializers.Serializer):
    user_id = serializers.UUIDField(required=False)
    organization_slug = serializers.SlugField(required=False)
    organization_id = serializers.UUIDField(required=False)

    def validate(self, attrs):
        if not attrs.get("user_id") and not attrs.get("organization_slug") and not attrs.get("organization_id"):
            request = self.context.get("request")
            if request and request.user and request.user.is_authenticated:
                attrs["user_id"] = request.user.id
            else:
                raise serializers.ValidationError("Provide user_id, organization_slug, or organization_id.")
        return attrs

    def save(self, **kwargs):
        request = self.context.get("request")
        subject = resolve_subject(
            user_id=self.validated_data.get("user_id"),
            organization_slug=self.validated_data.get("organization_slug"),
            organization_id=self.validated_data.get("organization_id"),
            actor=getattr(request, "user", None),
        )
        return product_access_summary(subject)
