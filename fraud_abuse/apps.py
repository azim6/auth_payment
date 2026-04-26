from django.apps import AppConfig


class FraudAbuseConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "fraud_abuse"
    verbose_name = "Fraud and Abuse Controls"
