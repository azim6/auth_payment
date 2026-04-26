from __future__ import annotations

import hashlib
from datetime import timedelta

from django.conf import settings
from django.template import Context, Template
from django.utils import timezone

from .models import (
    DevicePushToken,
    NotificationChannel,
    NotificationDelivery,
    NotificationEvent,
    NotificationPreference,
    NotificationProvider,
    NotificationSuppression,
    NotificationTemplate,
)


def hash_recipient(recipient: str) -> str:
    return hashlib.sha256(recipient.strip().lower().encode("utf-8")).hexdigest()


def render_string(template_text: str, payload: dict) -> str:
    if not template_text:
        return ""
    return Template(template_text).render(Context(payload))


def find_template(*, event: NotificationEvent, channel: str, locale: str = "en") -> NotificationTemplate | None:
    query = NotificationTemplate.objects.filter(key=event.event_type, channel=channel, is_active=True)
    if event.organization_id:
        scoped = query.filter(organization=event.organization, locale=locale).order_by("-version").first()
        if scoped:
            return scoped
    if event.project_id:
        project_template = query.filter(project=event.project, organization__isnull=True, locale=locale).order_by("-version").first()
        if project_template:
            return project_template
    return query.filter(organization__isnull=True, locale=locale).order_by("-version").first() or query.filter(organization__isnull=True, locale="en").order_by("-version").first()


def is_suppressed(*, channel: str, recipient: str) -> bool:
    recipient_hash = hash_recipient(recipient)
    return NotificationSuppression.objects.filter(channel=channel, recipient_hash=recipient_hash).filter(expires_at__isnull=True).exists() or NotificationSuppression.objects.filter(channel=channel, recipient_hash=recipient_hash, expires_at__gt=timezone.now()).exists()


def is_channel_enabled(*, event: NotificationEvent, channel: str) -> bool:
    if not event.user_id:
        return True
    preference = NotificationPreference.objects.filter(user=event.user, organization=event.organization, topic=event.topic, channel=channel).first()
    if preference is None:
        preference = NotificationPreference.objects.filter(user=event.user, organization__isnull=True, topic=event.topic, channel=channel).first()
    return preference.enabled if preference else True


def default_recipient(*, event: NotificationEvent, channel: str) -> str:
    if channel == NotificationChannel.EMAIL and event.user_id:
        return event.user.email
    if channel == NotificationChannel.PUSH and event.user_id:
        token = DevicePushToken.objects.filter(user=event.user, organization=event.organization, is_active=True).order_by("-created_at").first()
        return token.token_prefix if token else ""
    if channel == NotificationChannel.IN_APP and event.user_id:
        return str(event.user_id)
    return event.payload.get("recipient", "")


def select_provider(channel: str) -> NotificationProvider | None:
    return NotificationProvider.objects.filter(channel=channel, status=NotificationProvider.Status.ACTIVE).order_by("priority", "name").first()


def create_notification_event(*, event_type: str, topic: str, payload: dict | None = None, organization=None, user=None, project=None, priority: str = "normal", idempotency_key: str = "", created_by=None) -> NotificationEvent:
    if idempotency_key:
        event, created = NotificationEvent.objects.get_or_create(
            idempotency_key=idempotency_key,
            defaults={
                "event_type": event_type,
                "topic": topic,
                "payload": payload or {},
                "organization": organization,
                "user": user,
                "project": project,
                "priority": priority,
                "created_by": created_by,
            },
        )
        return event
    return NotificationEvent.objects.create(event_type=event_type, topic=topic, payload=payload or {}, organization=organization, user=user, project=project, priority=priority, created_by=created_by)


def enqueue_deliveries(event: NotificationEvent, channels: list[str] | None = None) -> list[NotificationDelivery]:
    channels = channels or list(NotificationChannel.values)
    created: list[NotificationDelivery] = []
    payload = dict(event.payload or {})
    payload.update({"event": event, "user": event.user, "organization": event.organization, "project": event.project})
    for channel in channels:
        if not is_channel_enabled(event=event, channel=channel):
            continue
        recipient = default_recipient(event=event, channel=channel)
        if not recipient or is_suppressed(channel=channel, recipient=recipient):
            continue
        template = find_template(event=event, channel=channel, locale=payload.get("locale", "en"))
        provider = select_provider(channel)
        subject = render_string(template.subject_template, payload) if template else payload.get("subject", "")
        body = render_string(template.body_template, payload) if template else payload.get("body", "")
        html_body = render_string(template.html_template, payload) if template else payload.get("html_body", "")
        delivery = NotificationDelivery.objects.create(
            event=event,
            template=template,
            provider=provider,
            channel=channel,
            recipient=recipient,
            recipient_hash=hash_recipient(recipient),
            subject=subject,
            body=body,
            html_body=html_body,
        )
        created.append(delivery)
    event.status = NotificationEvent.Status.QUEUED if created else NotificationEvent.Status.SKIPPED
    event.save(update_fields=["status", "updated_at"])
    return created


def mark_delivery_attempt(delivery: NotificationDelivery, *, success: bool, provider_message_id: str = "", error_message: str = "") -> NotificationDelivery:
    now = timezone.now()
    delivery.attempt_count += 1
    delivery.last_attempt_at = now
    if success:
        delivery.status = NotificationDelivery.Status.SENT
        delivery.sent_at = now
        delivery.provider_message_id = provider_message_id
        delivery.error_message = ""
        if delivery.provider_id:
            delivery.provider.last_success_at = now
            delivery.provider.save(update_fields=["last_success_at", "updated_at"])
    else:
        delivery.error_message = error_message
        if delivery.attempt_count >= delivery.max_attempts:
            delivery.status = NotificationDelivery.Status.DEAD
        else:
            delivery.status = NotificationDelivery.Status.FAILED
            delivery.next_attempt_at = now + timedelta(minutes=min(60, 2 ** delivery.attempt_count))
        if delivery.provider_id:
            delivery.provider.last_failure_at = now
            delivery.provider.save(update_fields=["last_failure_at", "updated_at"])
    delivery.save()
    return delivery


def dispatch_delivery(delivery: NotificationDelivery) -> NotificationDelivery:
    """Provider adapter placeholder. In production this calls SES/SendGrid/Twilio/FCM/APNs."""
    mode = getattr(settings, "NOTIFICATION_DELIVERY_MODE", "log")
    if mode == "disabled":
        delivery.status = NotificationDelivery.Status.SKIPPED
        delivery.error_message = "Notification delivery disabled by configuration."
        delivery.save(update_fields=["status", "error_message", "updated_at"])
        return delivery
    return mark_delivery_attempt(delivery, success=True, provider_message_id=f"local_{delivery.id}")
