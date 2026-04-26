from django.apps import AppConfig


class ProductionVerificationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "production_verification"
    verbose_name = "Production Verification"
