from .models import SdkCompatibilityMatrix, SdkRelease


def latest_published_releases():
    releases = {}
    for release in SdkRelease.objects.filter(status="published").order_by("platform", "-published_at", "-created_at"):
        releases.setdefault(release.platform, release)
    return releases


def sdk_summary():
    latest = latest_published_releases()
    compatibility_count = SdkCompatibilityMatrix.objects.count()
    return {
        "latest_releases": {
            platform: {
                "version": release.version,
                "download_url": release.download_url,
                "minimum_api_version": release.minimum_api_version,
                "published_at": release.published_at,
            }
            for platform, release in latest.items()
        },
        "compatibility_rows": compatibility_count,
        "supported_platforms": ["typescript", "android_kotlin", "windows_dotnet", "cli"],
    }
