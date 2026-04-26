from django.contrib import admin

from .models import AccountRestriction, SecurityIncident, SecurityRiskEvent


@admin.register(SecurityRiskEvent)
class SecurityRiskEventAdmin(admin.ModelAdmin):
    list_display = ("created_at", "category", "severity", "status", "signal", "score", "user", "organization")
    list_filter = ("category", "severity", "status", "signal", "created_at")
    search_fields = ("signal", "summary", "user__email", "organization__slug", "ip_address")
    readonly_fields = (
        "id", "category", "severity", "status", "signal", "score", "user", "organization",
        "subscription", "ip_address", "user_agent", "summary", "metadata", "acknowledged_by",
        "acknowledged_at", "resolved_by", "resolved_at", "created_at",
    )


@admin.register(AccountRestriction)
class AccountRestrictionAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "organization", "restriction_type", "starts_at", "expires_at", "lifted_at")
    list_filter = ("restriction_type", "starts_at", "expires_at", "lifted_at", "created_at")
    search_fields = ("user__email", "organization__slug", "reason")
    readonly_fields = ("id", "created_by", "lifted_by", "lifted_at", "created_at", "updated_at")


@admin.register(SecurityIncident)
class SecurityIncidentAdmin(admin.ModelAdmin):
    list_display = ("opened_at", "title", "severity", "status", "owner", "related_user", "related_organization")
    list_filter = ("severity", "status", "opened_at", "contained_at", "resolved_at", "closed_at")
    search_fields = ("title", "description", "owner__email", "related_user__email", "related_organization__slug")
    readonly_fields = ("id", "opened_at", "contained_at", "resolved_at", "closed_at", "created_at", "updated_at")
    filter_horizontal = ("risk_events",)
