from rest_framework import serializers
from .models import (
    Currency, Region, ExchangeRateSnapshot, TaxJurisdiction, TaxRate, TaxExemption,
    RegionalPrice, LocalizedInvoiceSetting, PriceResolutionRecord,
)


class CurrencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Currency
        fields = "__all__"


class RegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Region
        fields = "__all__"


class ExchangeRateSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExchangeRateSnapshot
        fields = "__all__"
        read_only_fields = ["created_by"]


class TaxJurisdictionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaxJurisdiction
        fields = "__all__"


class TaxRateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaxRate
        fields = "__all__"


class TaxExemptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaxExemption
        fields = "__all__"
        read_only_fields = ["verified_by", "verified_at", "created_at"]


class RegionalPriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegionalPrice
        fields = "__all__"


class LocalizedInvoiceSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = LocalizedInvoiceSetting
        fields = "__all__"


class PriceResolutionRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = PriceResolutionRecord
        fields = "__all__"
        read_only_fields = ["created_at"]


class PriceResolutionRequestSerializer(serializers.Serializer):
    plan_id = serializers.IntegerField()
    region_code = serializers.CharField(max_length=16)
    organization_id = serializers.IntegerField(required=False)
    user_id = serializers.IntegerField(required=False)
