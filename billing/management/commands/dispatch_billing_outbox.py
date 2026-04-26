from django.core.management.base import BaseCommand

from billing.services import dispatch_due_outbox_events


class Command(BaseCommand):
    help = "Dispatch due billing outbox events. Intended for cron/Celery beat/Kubernetes jobs."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=100)
        parser.add_argument("--event-type", default="")

    def handle(self, *args, **options):
        result = dispatch_due_outbox_events(limit=options["limit"], event_type=options["event_type"])
        self.stdout.write(self.style.SUCCESS(f"Dispatched billing outbox: {result}"))
