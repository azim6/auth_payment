from celery import shared_task

from .services import dispatch_due_outbox_events


@shared_task(bind=True, max_retries=3)
def dispatch_billing_outbox_task(self, limit=100, event_type=""):
    """Dispatch due billing outbox events on a schedule."""
    return dispatch_due_outbox_events(limit=limit, event_type=event_type)
