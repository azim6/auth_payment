from django.contrib import admin

from .models import AbuseCase, AbuseSignal, DeviceFingerprint, IPReputation, PaymentRiskReview, VelocityEvent, VelocityRule


@admin.register(DeviceFingerprint)
class DeviceFingerprintAdmin(admin.ModelAdmin):
    list_display = ("fingerprint_hash", "trust_level", "last_user", "last_organization", "last_seen_at")
    list_filter = ("trust_level", "created_at", "last_seen_at")
    search_fields = ("fingerprint_hash", "last_user__email", "last_organization__name")
    readonly_fields = ("id", "created_at", "updated_at", "first_seen_at")


@admin.register(IPReputation)
class IPReputationAdmin(admin.ModelAdmin):
    list_display = ("ip_address", "reputation", "risk_score", "country_code", "source", "last_seen_at")
    list_filter = ("reputation", "source", "country_code")
    search_fields = ("ip_address", "asn", "source")
    readonly_fields = ("id", "created_at", "updated_at", "first_seen_at", "is_active")


@admin.register(AbuseSignal)
class AbuseSignalAdmin(admin.ModelAdmin):
    list_display = ("category", "signal", "severity", "score", "user", "organization", "observed_at")
    list_filter = ("category", "severity", "signal")
    search_fields = ("signal", "summary", "user__email", "organization__name", "ip_address")
    readonly_fields = ("id", "created_at")


@admin.register(VelocityRule)
class VelocityRuleAdmin(admin.ModelAdmin):
    list_display = ("name", "event_name", "scope", "threshold", "window_seconds", "action", "enabled")
    list_filter = ("scope", "action", "enabled")
    search_fields = ("name", "event_name")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(VelocityEvent)
class VelocityEventAdmin(admin.ModelAdmin):
    list_display = ("event_name", "user", "organization", "ip_address", "occurred_at")
    list_filter = ("event_name", "occurred_at")
    search_fields = ("event_name", "user__email", "organization__name", "ip_address")
    readonly_fields = ("id", "created_at")


@admin.register(AbuseCase)
class AbuseCaseAdmin(admin.ModelAdmin):
    list_display = ("title", "case_type", "status", "severity", "user", "organization", "opened_at")
    list_filter = ("case_type", "status", "severity")
    search_fields = ("title", "summary", "user__email", "organization__name")
    filter_horizontal = ("signals",)
    readonly_fields = ("id", "opened_at", "resolved_at", "created_at", "updated_at")


@admin.register(PaymentRiskReview)
class PaymentRiskReviewAdmin(admin.ModelAdmin):
    list_display = ("organization", "status", "risk_score", "reviewed_by", "reviewed_at", "created_at")
    list_filter = ("status", "risk_score")
    search_fields = ("organization__name", "reason", "decision_notes")
    filter_horizontal = ("signals",)
    readonly_fields = ("id", "reviewed_by", "reviewed_at", "created_at", "updated_at")
