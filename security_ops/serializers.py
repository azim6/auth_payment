from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Q
from rest_framework import serializers

from accounts.models import Organization
from admin_integration.permissions import request_actor_user, request_admin_audit_metadata
from billing.models import Subscription

from .models import AccountRestriction, SecurityIncident, SecurityRiskEvent
from .services import create_risk_event, log_security_admin_action

User = get_user_model()


class SecurityRiskEventSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    organization_slug = serializers.SlugField(source="organization.slug", read_only=True)

    class Meta:
        model = SecurityRiskEvent
        fields = [
            "id", "category", "severity", "status", "signal", "score", "summary",
            "user", "user_email", "organization", "organization_slug", "subscription",
            "ip_address", "user_agent", "metadata", "acknowledged_by", "acknowledged_at",
            "resolved_by", "resolved_at", "created_at",
        ]
        read_only_fields = [
            "id", "severity", "status", "user_email", "organization_slug", "ip_address",
            "user_agent", "acknowledged_by", "acknowledged_at", "resolved_by", "resolved_at", "created_at",
        ]

    def validate_score(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError("Risk score must be between 0 and 100.")
        return value

    def create(self, validated_data):
        request = self.context.get("request")
        event = create_risk_event(request=request, **validated_data)
        log_security_admin_action(
            request=request,
            action="security_risk_event.created",
            metadata={"event_id": str(event.id), "signal": event.signal, "score": event.score},
        )
        return event


class SecurityRiskEventActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["acknowledge", "resolve", "false_positive"])

    def save(self, **kwargs):
        request = self.context["request"]
        event = self.context["event"]
        action = self.validated_data["action"]
        if action == "acknowledge":
            event.acknowledge(request.user)
        elif action == "false_positive":
            event.resolve(request.user, false_positive=True)
        else:
            event.resolve(request.user)
        log_security_admin_action(
            request=request,
            action=f"security_risk_event.{action}",
            metadata={"event_id": str(event.id), "signal": event.signal},
        )
        return event


class AccountRestrictionSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    organization_slug = serializers.SlugField(source="organization.slug", read_only=True)
    active = serializers.BooleanField(source="is_active", read_only=True)

    class Meta:
        model = AccountRestriction
        fields = [
            "id", "user", "user_email", "organization", "organization_slug", "restriction_type",
            "reason", "metadata", "starts_at", "expires_at", "lifted_at", "created_by", "lifted_by",
            "active", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "user_email", "organization_slug", "lifted_at", "created_by", "lifted_by",
            "active", "created_at", "updated_at",
        ]

    def validate(self, attrs):
        starts_at = attrs.get("starts_at") or timezone.now()
        expires_at = attrs.get("expires_at")
        if expires_at and expires_at <= starts_at:
            raise serializers.ValidationError("expires_at must be after starts_at.")
        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        restriction = AccountRestriction.objects.create(
            created_by=request_actor_user(request),
            metadata={**validated_data.get("metadata", {}), **request_admin_audit_metadata(request)},
            **{key: value for key, value in validated_data.items() if key != "metadata"},
        )
        log_security_admin_action(
            request=request,
            action="account_restriction.created",
            metadata={
                "restriction_id": str(restriction.id),
                "user_id": str(restriction.user_id),
                "organization_id": str(restriction.organization_id) if restriction.organization_id else None,
                "restriction_type": restriction.restriction_type,
            },
        )
        return restriction


class AccountRestrictionLiftSerializer(serializers.Serializer):
    def save(self, **kwargs):
        request = self.context["request"]
        restriction = self.context["restriction"]
        restriction.lift(request.user)
        log_security_admin_action(
            request=request,
            action="account_restriction.lifted",
            metadata={"restriction_id": str(restriction.id), "user_id": str(restriction.user_id)},
        )
        return restriction


class SecurityIncidentSerializer(serializers.ModelSerializer):
    owner_email = serializers.EmailField(source="owner.email", read_only=True)
    related_user_email = serializers.EmailField(source="related_user.email", read_only=True)
    related_organization_slug = serializers.SlugField(source="related_organization.slug", read_only=True)

    class Meta:
        model = SecurityIncident
        fields = [
            "id", "title", "severity", "status", "owner", "owner_email", "related_user",
            "related_user_email", "related_organization", "related_organization_slug", "risk_events",
            "description", "containment_notes", "resolution_notes", "opened_at", "contained_at",
            "resolved_at", "closed_at", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "owner_email", "related_user_email", "related_organization_slug", "created_at", "updated_at"]

    def create(self, validated_data):
        request = self.context["request"]
        incident = super().create(validated_data)
        log_security_admin_action(
            request=request,
            action="security_incident.created",
            metadata={"incident_id": str(incident.id), "severity": incident.severity, "status": incident.status},
        )
        return incident

    def update(self, instance, validated_data):
        previous_status = instance.status
        instance = super().update(instance, validated_data)
        now = timezone.now()
        update_fields = []
        if instance.status == SecurityIncident.Status.CONTAINED and not instance.contained_at:
            instance.contained_at = now
            update_fields.append("contained_at")
        if instance.status == SecurityIncident.Status.RESOLVED and not instance.resolved_at:
            instance.resolved_at = now
            update_fields.append("resolved_at")
        if instance.status == SecurityIncident.Status.CLOSED and not instance.closed_at:
            instance.closed_at = now
            update_fields.append("closed_at")
        if update_fields:
            instance.save(update_fields=update_fields + ["updated_at"])
        if previous_status != instance.status:
            log_security_admin_action(
                request=self.context["request"],
                action="security_incident.status_changed",
                metadata={"incident_id": str(instance.id), "from": previous_status, "to": instance.status},
            )
        return instance


class UserSecurityStateSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    organization_id = serializers.UUIDField(required=False)
    active_restrictions = AccountRestrictionSerializer(many=True, read_only=True)
    open_risk_events = SecurityRiskEventSerializer(many=True, read_only=True)
    open_incidents = SecurityIncidentSerializer(many=True, read_only=True)

    def validate_user_id(self, value):
        if not User.objects.filter(id=value).exists():
            raise serializers.ValidationError("User not found.")
        return value

    def validate_organization_id(self, value):
        if value and not Organization.objects.filter(id=value).exists():
            raise serializers.ValidationError("Organization not found.")
        return value

    def save(self, **kwargs):
        user_id = self.validated_data["user_id"]
        org_id = self.validated_data.get("organization_id")
        now = timezone.now()
        restrictions = AccountRestriction.objects.filter(user_id=user_id, lifted_at__isnull=True, starts_at__lte=now).filter(
            Q(expires_at__isnull=True) | Q(expires_at__gt=now)
        )
        events = SecurityRiskEvent.objects.filter(user_id=user_id, status__in=[SecurityRiskEvent.Status.OPEN, SecurityRiskEvent.Status.ACKNOWLEDGED])
        incidents = SecurityIncident.objects.filter(related_user_id=user_id).exclude(status__in=[SecurityIncident.Status.RESOLVED, SecurityIncident.Status.CLOSED])
        if org_id:
            restrictions = restrictions.filter(organization_id__in=[org_id, None])
            events = events.filter(organization_id=org_id)
            incidents = incidents.filter(related_organization_id=org_id)
        return {
            "user_id": user_id,
            "organization_id": org_id,
            "active_restrictions": restrictions,
            "open_risk_events": events,
            "open_incidents": incidents,
        }
