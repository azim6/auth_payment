from django.core.management.base import BaseCommand
from django.utils import timezone

from billing.models import ProviderSyncState


class Command(BaseCommand):
    help = "Print provider sync health for billing operators and monitoring jobs."

    def handle(self, *args, **options):
        now = timezone.now()
        unhealthy = ProviderSyncState.objects.exclude(status=ProviderSyncState.Status.HEALTHY).count()
        total = ProviderSyncState.objects.count()
        self.stdout.write(f"billing_sync_health total={total} unhealthy={unhealthy} checked_at={now.isoformat()}")
        for state in ProviderSyncState.objects.order_by("provider", "resource_type"):
            self.stdout.write(f"{state.provider}.{state.resource_type} status={state.status} lag={state.lag_seconds}s errors={state.error_count}")
