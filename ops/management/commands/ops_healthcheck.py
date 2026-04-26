from django.core.management.base import BaseCommand

from ops.services import build_readiness_payload


class Command(BaseCommand):
    help = "Run production readiness and health checks."

    def handle(self, *args, **options):
        payload = build_readiness_payload()
        self.stdout.write(str(payload))
        if not payload["ready"]:
            raise SystemExit(1)
