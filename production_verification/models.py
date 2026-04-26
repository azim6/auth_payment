from django.conf import settings
from django.db import models
from django.utils import timezone


class VerificationSnapshot(models.Model):
    STATUS_PASS = "pass"
    STATUS_WARN = "warn"
    STATUS_FAIL = "fail"
    STATUS_CHOICES = [(STATUS_PASS, "Pass"), (STATUS_WARN, "Warn"), (STATUS_FAIL, "Fail")]

    id = models.BigAutoField(primary_key=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES)
    summary = models.JSONField(default=dict, blank=True)
    checks = models.JSONField(default=list, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Production verification {self.status} at {self.created_at:%Y-%m-%d %H:%M:%S}"


class FeatureFlagInventory(models.Model):
    TIER_PRODUCTION = "production"
    TIER_OPTIONAL = "optional"
    TIER_EXPERIMENTAL = "experimental"
    TIER_CHOICES = [
        (TIER_PRODUCTION, "Production MVP"),
        (TIER_OPTIONAL, "Optional"),
        (TIER_EXPERIMENTAL, "Experimental"),
    ]

    app_label = models.CharField(max_length=96, unique=True)
    tier = models.CharField(max_length=24, choices=TIER_CHOICES, default=TIER_OPTIONAL)
    enabled_by_default = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["tier", "app_label"]

    def __str__(self):
        return f"{self.app_label} ({self.tier})"
