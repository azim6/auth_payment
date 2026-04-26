from __future__ import annotations

from typing import Iterable

from django.utils import timezone

from accounts.models import Organization, OrganizationMembership

from .models import DeveloperApplication, IntegrationAuditEvent, WebhookDelivery, WebhookSubscription


def user_can_manage_platform(user, organization: Organization) -> bool:
    if not user or not user.is_authenticated:
        return False
    if user.is_staff:
        return True
    return OrganizationMembership.objects.filter(
        organization=organization,
        user=user,
        is_active=True,
        role__in=[OrganizationMembership.Role.OWNER, OrganizationMembership.Role.ADMIN],
    ).exists()


def create_integration_audit_event(*, organization, actor, action: str, application=None, request=None, metadata=None, target_type="", target_id=""):
    ip_address = None
    user_agent = ""
    if request is not None:
        ip_address = request.META.get("HTTP_X_FORWARDED_FOR", request.META.get("REMOTE_ADDR", "")).split(",")[0] or None
        user_agent = request.META.get("HTTP_USER_AGENT", "")[:2000]
    return IntegrationAuditEvent.objects.create(
        organization=organization,
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        application=application,
        action=action,
        target_type=target_type,
        target_id=str(target_id or ""),
        ip_address=ip_address,
        user_agent=user_agent,
        metadata=metadata or {},
    )


def create_application_with_secret(*, organization, created_by, request=None, **kwargs):
    raw_secret = None
    app = DeveloperApplication(
        organization=organization,
        created_by=created_by if getattr(created_by, "is_authenticated", False) else None,
        client_id=DeveloperApplication.generate_client_id(),
        **kwargs,
    )
    if kwargs.get("app_type") in {DeveloperApplication.AppType.WEB, DeveloperApplication.AppType.SERVICE}:
        raw_secret = DeveloperApplication.generate_client_secret()
        app.set_client_secret(raw_secret)
    app.save()
    create_integration_audit_event(
        organization=organization,
        actor=created_by,
        action="developer_application.created",
        application=app,
        request=request,
        target_type="developer_application",
        target_id=app.id,
    )
    return app, raw_secret


def rotate_application_secret(*, application: DeveloperApplication, actor, request=None):
    raw_secret = DeveloperApplication.generate_client_secret()
    application.set_client_secret(raw_secret)
    application.save(update_fields=["client_secret_hash", "client_secret_prefix", "updated_at"])
    create_integration_audit_event(
        organization=application.organization,
        actor=actor,
        action="developer_application.secret_rotated",
        application=application,
        request=request,
        target_type="developer_application",
        target_id=application.id,
    )
    return raw_secret


def create_webhook_subscription_with_secret(*, organization, application, created_by, request=None, **kwargs):
    raw_secret = WebhookSubscription.generate_secret()
    subscription = WebhookSubscription(organization=organization, application=application, created_by=created_by, **kwargs)
    subscription.set_secret(raw_secret)
    subscription.save()
    create_integration_audit_event(
        organization=organization,
        actor=created_by,
        action="webhook_subscription.created",
        application=application,
        request=request,
        target_type="webhook_subscription",
        target_id=subscription.id,
    )
    return subscription, raw_secret


def rotate_webhook_secret(*, subscription: WebhookSubscription, actor, request=None):
    raw_secret = WebhookSubscription.generate_secret()
    subscription.set_secret(raw_secret)
    subscription.save(update_fields=["secret_hash", "secret_prefix", "updated_at"])
    create_integration_audit_event(
        organization=subscription.organization,
        actor=actor,
        action="webhook_subscription.secret_rotated",
        application=subscription.application,
        request=request,
        target_type="webhook_subscription",
        target_id=subscription.id,
    )
    return raw_secret


def enqueue_webhook_event(*, organization: Organization, event_type: str, payload: dict, applications: Iterable[DeveloperApplication] | None = None):
    subscriptions = WebhookSubscription.objects.filter(organization=organization, status=WebhookSubscription.Status.ACTIVE)
    if applications is not None:
        subscriptions = subscriptions.filter(application__in=list(applications))
    deliveries = []
    for subscription in subscriptions.select_related("application"):
        if event_type not in subscription.event_types:
            continue
        deliveries.append(WebhookDelivery.objects.create(subscription=subscription, event_type=event_type, payload=payload, next_attempt_at=timezone.now()))
    return deliveries
