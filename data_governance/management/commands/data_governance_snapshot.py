from django.core.management.base import BaseCommand

from data_governance.services import create_inventory_snapshot, governance_summary


class Command(BaseCommand):
    help = "Create a data-governance inventory snapshot and print the current summary."

    def handle(self, *args, **options):
        snapshot = create_inventory_snapshot(user=None)
        self.stdout.write(self.style.SUCCESS(f"created_snapshot={snapshot.id}"))
        self.stdout.write(str(governance_summary()))
