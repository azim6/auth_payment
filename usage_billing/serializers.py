from rest_framework import serializers

from .models import (
    CreditApplication,
    CreditGrant,
    Meter,
    MeterPrice,
    RatedUsageLine,
    UsageAggregationWindow,
    UsageEvent,
    UsageReconciliationRun,
)


class MeterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Meter
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class MeterPriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = MeterPrice
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class UsageEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = UsageEvent
        fields = "__all__"
        read_only_fields = ["id", "created_at"]


class UsageAggregationWindowSerializer(serializers.ModelSerializer):
    class Meta:
        model = UsageAggregationWindow
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "finalized_at"]


class RatedUsageLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = RatedUsageLine
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class CreditGrantSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreditGrant
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "created_by"]


class CreditApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreditApplication
        fields = "__all__"
        read_only_fields = ["id", "created_at"]


class UsageReconciliationRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = UsageReconciliationRun
        fields = "__all__"
        read_only_fields = ["id", "created_at", "completed_at", "created_by"]


class UsageIngestSerializer(serializers.Serializer):
    organization = serializers.UUIDField()
    meter_code = serializers.CharField(max_length=120)
    quantity = serializers.DecimalField(max_digits=18, decimal_places=6, default="1")
    occurred_at = serializers.DateTimeField(required=False)
    idempotency_key = serializers.CharField(max_length=180)
    source = serializers.CharField(max_length=80, default="api")
    attributes = serializers.JSONField(required=False, default=dict)


class UsageWindowPlanSerializer(serializers.Serializer):
    subscription = serializers.UUIDField()
    meter = serializers.UUIDField()
    window_start = serializers.DateTimeField()
    window_end = serializers.DateTimeField()


class RateUsageWindowSerializer(serializers.Serializer):
    window = serializers.UUIDField()
    meter_price = serializers.UUIDField()
    apply_credits = serializers.BooleanField(default=True)


class UsageSummarySerializer(serializers.Serializer):
    organization = serializers.CharField()
    open_windows = serializers.IntegerField()
    finalized_windows = serializers.IntegerField()
    ready_rated_lines = serializers.IntegerField()
    active_credit_cents = serializers.IntegerField()
