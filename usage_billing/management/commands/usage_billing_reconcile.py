from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_datetime

from usage_billing.services import create_reconciliation_run


class Command(BaseCommand):
    help = "Create a usage billing reconciliation run for a time window."

    def add_arguments(self, parser):
        parser.add_argument("--provider", default="stripe")
        parser.add_argument("--window-start", required=True)
        parser.add_argument("--window-end", required=True)

    def handle(self, *args, **options):
        run = create_reconciliation_run(provider=options["provider"], window_start=parse_datetime(options["window_start"]), window_end=parse_datetime(options["window_end"]))
        self.stdout.write(self.style.SUCCESS(f"created usage reconciliation {run.id}"))
