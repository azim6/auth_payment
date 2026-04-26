from django.core.management.base import BaseCommand
from django.test import RequestFactory

from oidc_provider.services import create_metadata_snapshot


class Command(BaseCommand):
    help = "Create an OIDC discovery metadata snapshot for operational evidence."

    def add_arguments(self, parser):
        parser.add_argument("--host", default="auth.example.com", help="Issuer host used to build absolute URLs.")
        parser.add_argument("--scheme", default="https", choices=["http", "https"], help="Issuer scheme.")

    def handle(self, *args, **options):
        request = RequestFactory().get("/", secure=options["scheme"] == "https", HTTP_HOST=options["host"])
        snapshot = create_metadata_snapshot(request)
        self.stdout.write(self.style.SUCCESS(f"created OIDC metadata snapshot {snapshot.id} for {snapshot.issuer}"))
