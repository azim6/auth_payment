from celery import shared_task

from billing.models import Subscription
from .models import Meter
from .services import aggregate_window


@shared_task
def aggregate_usage_window(subscription_id, meter_id, window_start_iso, window_end_iso):
    from django.utils.dateparse import parse_datetime

    subscription = Subscription.objects.get(id=subscription_id)
    meter = Meter.objects.get(id=meter_id)
    window = aggregate_window(subscription=subscription, meter=meter, window_start=parse_datetime(window_start_iso), window_end=parse_datetime(window_end_iso))
    return str(window.id)
