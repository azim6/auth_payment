from django.core.management.base import BaseCommand

from ops.models import ReleaseRecord


class Command(BaseCommand):
    help = "Create or update a release metadata record."

    def add_arguments(self, parser):
        parser.add_argument("version")
        parser.add_argument("--git-sha", default="")
        parser.add_argument("--image-tag", default="")
        parser.add_argument("--status", default=ReleaseRecord.Status.STAGED)

    def handle(self, *args, **options):
        release, _ = ReleaseRecord.objects.update_or_create(
            version=options["version"],
            defaults={"git_sha": options["git_sha"], "image_tag": options["image_tag"], "status": options["status"]},
        )
        self.stdout.write(f"release={release.version} status={release.status}")
