import json

from django.core.management.base import BaseCommand, CommandError

from production_verification.checks import run_production_verification
from production_verification.models import VerificationSnapshot


class Command(BaseCommand):
    help = "Run production verification checks for the auth/payment platform."

    def add_arguments(self, parser):
        parser.add_argument("--persist", action="store_true", help="Persist a VerificationSnapshot row.")
        parser.add_argument("--fail-on-warn", action="store_true", help="Exit non-zero for warnings as well as failures.")

    def handle(self, *args, **options):
        result = run_production_verification()
        self.stdout.write(json.dumps(result, indent=2, sort_keys=True))
        if options["persist"]:
            VerificationSnapshot.objects.create(status=result["status"], summary=result["summary"], checks=result["checks"])
        if result["status"] == "fail" or (options["fail_on_warn"] and result["status"] == "warn"):
            raise CommandError(f"Production verification status: {result['status']}")
