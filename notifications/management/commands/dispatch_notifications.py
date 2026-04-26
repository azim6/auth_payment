from django.core.management.base import BaseCommand

from notifications.tasks import dispatch_due_notifications


class Command(BaseCommand):
    help = "Dispatch pending notification deliveries using the configured provider adapter."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=100)

    def handle(self, *args, **options):
        count = dispatch_due_notifications(limit=options["limit"])
        self.stdout.write(self.style.SUCCESS(f"Dispatched {count} notification deliveries."))
