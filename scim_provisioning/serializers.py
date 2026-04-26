from django.utils import timezone
from rest_framework import serializers

from accounts.models import Organization, OrganizationMembership
from .models import (
    DeprovisioningPolicy,
    DirectoryGroup,
    DirectoryGroupMember,
    DirectoryUser,
    ScimApplication,
    ScimProvisioningEvent,
    ScimSyncJob,
)


class OrganizationSlugField(serializers.SlugRelatedField):
    def __init__(self, **kwargs):
        super().__init__(slug_field="slug", queryset=Organization.objects.all(), **kwargs)


class ScimApplicationSerializer(serializers.ModelSerializer):
    organization = OrganizationSlugField()
    created_by_email = serializers.EmailField(source="created_by.email", read_only=True)
    raw_token = serializers.CharField(read_only=True)

    class Meta:
        model = ScimApplication
        fields = [
            "id",
            "organization",
            "name",
            "slug",
            "provider",
            "status",
            "token_prefix",
            "raw_token",
            "default_role",
            "allow_create_users",
            "allow_update_users",
            "allow_deactivate_users",
            "allow_group_sync",
            "require_verified_domain",
            "allowed_email_domains",
            "attribute_mapping",
            "created_by_email",
            "last_used_at",
            "activated_at",
            "revoked_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["status", "token_prefix", "raw_token", "created_by_email", "last_used_at", "activated_at", "revoked_at", "created_at", "updated_at"]

    def validate_default_role(self, value):
        allowed = {choice[0] for choice in OrganizationMembership.Role.choices}
        if value not in allowed:
            raise serializers.ValidationError("default_role must be a valid organization role.")
        return value

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        app = super().create(validated_data)
        raw_token = app.rotate_token()
        app.raw_token = raw_token
        return app


class DirectoryUserSerializer(serializers.ModelSerializer):
    organization = OrganizationSlugField()
    local_user_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = DirectoryUser
        fields = [
            "id",
            "organization",
            "scim_application",
            "user",
            "local_user_email",
            "external_id",
            "user_name",
            "email",
            "display_name",
            "given_name",
            "family_name",
            "status",
            "active",
            "raw_attributes",
            "last_synced_at",
            "deprovisioned_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["local_user_email", "last_synced_at", "deprovisioned_at", "created_at", "updated_at"]


class DirectoryGroupMemberSerializer(serializers.ModelSerializer):
    directory_user_email = serializers.EmailField(source="directory_user.email", read_only=True)

    class Meta:
        model = DirectoryGroupMember
        fields = ["id", "organization", "group", "directory_user", "directory_user_email", "external_user_id", "created_at"]
        read_only_fields = ["created_at", "directory_user_email"]


class DirectoryGroupSerializer(serializers.ModelSerializer):
    organization = OrganizationSlugField()
    member_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = DirectoryGroup
        fields = [
            "id",
            "organization",
            "scim_application",
            "external_id",
            "display_name",
            "status",
            "mapped_role",
            "mapped_permissions",
            "raw_attributes",
            "last_synced_at",
            "member_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["last_synced_at", "member_count", "created_at", "updated_at"]

    def validate_mapped_role(self, value):
        if value:
            allowed = {choice[0] for choice in OrganizationMembership.Role.choices}
            if value not in allowed:
                raise serializers.ValidationError("mapped_role must be blank or a valid organization role.")
        return value


class DeprovisioningPolicySerializer(serializers.ModelSerializer):
    organization = OrganizationSlugField()
    updated_by_email = serializers.EmailField(source="updated_by.email", read_only=True)

    class Meta:
        model = DeprovisioningPolicy
        fields = [
            "id",
            "organization",
            "action",
            "grace_period_hours",
            "preserve_billing_owner",
            "notify_admins",
            "require_approval_for_owners",
            "updated_by_email",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["updated_by_email", "created_at", "updated_at"]

    def create(self, validated_data):
        validated_data["updated_by"] = self.context["request"].user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data["updated_by"] = self.context["request"].user
        return super().update(instance, validated_data)


class ScimSyncJobSerializer(serializers.ModelSerializer):
    organization = OrganizationSlugField()
    requested_by_email = serializers.EmailField(source="requested_by.email", read_only=True)

    class Meta:
        model = ScimSyncJob
        fields = [
            "id",
            "organization",
            "scim_application",
            "status",
            "mode",
            "dry_run",
            "users_seen",
            "users_created",
            "users_updated",
            "users_deprovisioned",
            "groups_seen",
            "groups_updated",
            "errors",
            "started_at",
            "finished_at",
            "requested_by_email",
            "created_at",
        ]
        read_only_fields = ["status", "users_seen", "users_created", "users_updated", "users_deprovisioned", "groups_seen", "groups_updated", "errors", "started_at", "finished_at", "requested_by_email", "created_at"]

    def create(self, validated_data):
        validated_data["requested_by"] = self.context["request"].user
        return super().create(validated_data)


class ScimProvisioningEventSerializer(serializers.ModelSerializer):
    organization_slug = serializers.CharField(source="organization.slug", read_only=True)
    actor_email = serializers.EmailField(source="actor.email", read_only=True)

    class Meta:
        model = ScimProvisioningEvent
        fields = [
            "id",
            "organization",
            "organization_slug",
            "scim_application",
            "actor_email",
            "directory_user",
            "directory_group",
            "event_type",
            "result",
            "external_id",
            "message",
            "payload",
            "ip_address",
            "user_agent",
            "created_at",
        ]
        read_only_fields = fields


class ScimUserUpsertSerializer(serializers.Serializer):
    external_id = serializers.CharField(max_length=255)
    user_name = serializers.EmailField()
    email = serializers.EmailField()
    display_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    given_name = serializers.CharField(max_length=120, required=False, allow_blank=True)
    family_name = serializers.CharField(max_length=120, required=False, allow_blank=True)
    active = serializers.BooleanField(default=True)
    attributes = serializers.JSONField(default=dict, required=False)

    def save(self, *, application: ScimApplication):
        if not application.allow_create_users and not DirectoryUser.objects.filter(organization=application.organization, external_id=self.validated_data["external_id"]).exists():
            raise serializers.ValidationError("This SCIM application cannot create users.")
        if not application.allow_update_users and DirectoryUser.objects.filter(organization=application.organization, external_id=self.validated_data["external_id"]).exists():
            raise serializers.ValidationError("This SCIM application cannot update users.")
        data = self.validated_data
        obj, created = DirectoryUser.objects.update_or_create(
            organization=application.organization,
            external_id=data["external_id"],
            defaults={
                "scim_application": application,
                "user_name": data["user_name"],
                "email": data["email"],
                "display_name": data.get("display_name", ""),
                "given_name": data.get("given_name", ""),
                "family_name": data.get("family_name", ""),
                "active": data.get("active", True),
                "status": DirectoryUser.Status.ACTIVE if data.get("active", True) else DirectoryUser.Status.SUSPENDED,
                "raw_attributes": data.get("attributes", {}),
                "last_synced_at": timezone.now(),
            },
        )
        return obj, created


class ScimUserDeactivateSerializer(serializers.Serializer):
    external_id = serializers.CharField(max_length=255)
    reason = serializers.CharField(max_length=255, required=False, allow_blank=True)

    def save(self, *, application: ScimApplication):
        if not application.allow_deactivate_users:
            raise serializers.ValidationError("This SCIM application cannot deactivate users.")
        obj = DirectoryUser.objects.get(organization=application.organization, external_id=self.validated_data["external_id"])
        obj.mark_deprovisioned()
        return obj


class ScimGroupUpsertSerializer(serializers.Serializer):
    external_id = serializers.CharField(max_length=255)
    display_name = serializers.CharField(max_length=255)
    mapped_role = serializers.ChoiceField(choices=OrganizationMembership.Role.choices, required=False, allow_blank=True)
    attributes = serializers.JSONField(default=dict, required=False)
    member_external_ids = serializers.ListField(child=serializers.CharField(max_length=255), required=False, default=list)

    def save(self, *, application: ScimApplication):
        if not application.allow_group_sync:
            raise serializers.ValidationError("This SCIM application cannot sync groups.")
        data = self.validated_data
        group, created = DirectoryGroup.objects.update_or_create(
            organization=application.organization,
            external_id=data["external_id"],
            defaults={
                "scim_application": application,
                "display_name": data["display_name"],
                "mapped_role": data.get("mapped_role", ""),
                "raw_attributes": data.get("attributes", {}),
                "last_synced_at": timezone.now(),
                "status": DirectoryGroup.Status.ACTIVE,
            },
        )
        linked = 0
        for external_user_id in data.get("member_external_ids", []):
            try:
                directory_user = DirectoryUser.objects.get(organization=application.organization, external_id=external_user_id)
            except DirectoryUser.DoesNotExist:
                continue
            DirectoryGroupMember.objects.get_or_create(
                organization=application.organization,
                group=group,
                directory_user=directory_user,
                defaults={"external_user_id": external_user_id},
            )
            linked += 1
        group.linked_member_count = linked
        return group, created
