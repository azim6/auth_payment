from celery import shared_task
from django.utils import timezone

from .models import NotificationDelivery, NotificationEvent
from .services import dispatch_delivery, enqueue_deliveries


@shared_task
def enqueue_event_deliveries(event_id: str, channels: list[str] | None = None) -> int:
    event = NotificationEvent.objects.get(id=event_id)
    return len(enqueue_deliveries(event, channels=channels))


@shared_task
def dispatch_due_notifications(limit: int = 100) -> int:
    deliveries = NotificationDelivery.objects.filter(status__in=[NotificationDelivery.Status.PENDING, NotificationDelivery.Status.FAILED], next_attempt_at__lte=timezone.now()).order_by("next_attempt_at")[:limit]
    count = 0
    for delivery in deliveries:
        dispatch_delivery(delivery)
        count += 1
    return count
