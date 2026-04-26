from django.test import TestCase

from .models import SdkRelease
from .services import sdk_summary


class SdkRegistryTests(TestCase):
    def test_latest_release_summary(self):
        release = SdkRelease.objects.create(platform="typescript", version="0.1.0", status="published")
        release.publish()
        summary = sdk_summary()
        self.assertEqual(summary["latest_releases"]["typescript"]["version"], "0.1.0")
