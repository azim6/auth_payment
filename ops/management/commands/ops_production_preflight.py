from __future__ import annotations

import json

from django.core.management.base import BaseCommand

from ops.services import build_production_boot_validation_payload


class Command(BaseCommand):
    help = "Run v40 production boot validation checks and exit non-zero if strict checks fail."

    def add_arguments(self, parser):
        parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")

    def handle(self, *args, **options):
        payload = build_production_boot_validation_payload()
        if options["json"]:
            self.stdout.write(json.dumps(payload, indent=2, sort_keys=True))
        else:
            self.stdout.write(f"ready={payload['ready']} version={payload['version']}")
            for check in payload["checks"]:
                self.stdout.write(f"{check['status'].upper():4} {check['key']}: {check['message']}")
        if not payload["ready"]:
            raise SystemExit(1)
