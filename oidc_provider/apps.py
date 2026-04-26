from django.apps import AppConfig


class OidcProviderConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "oidc_provider"
    verbose_name = "OIDC Provider Hardening"
