from rest_framework import serializers

from .models import FeatureFlagInventory, VerificationSnapshot


class VerificationSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = VerificationSnapshot
        fields = ["id", "status", "summary", "checks", "created_by", "created_at"]
        read_only_fields = fields


class FeatureFlagInventorySerializer(serializers.ModelSerializer):
    class Meta:
        model = FeatureFlagInventory
        fields = ["id", "app_label", "tier", "enabled_by_default", "notes", "updated_at"]
        read_only_fields = ["id", "updated_at"]
