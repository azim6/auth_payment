from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

from .models import AccountToken, User
from .tokens import build_action_url, issue_account_token


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def send_email_verification_task(self, user_id: str) -> None:
    user = User.objects.get(pk=user_id)
    token = issue_account_token(user, AccountToken.Purpose.EMAIL_VERIFICATION, timedelta(hours=24))
    url = build_action_url(settings.EMAIL_VERIFICATION_URL, token)
    send_mail(
        subject="Verify your email address",
        message=(
            "Welcome. Verify your email address using this link:\n\n"
            f"{url}\n\n"
            "This link expires in 24 hours. If you did not create this account, ignore this email."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def send_password_reset_task(self, user_id: str) -> None:
    user = User.objects.get(pk=user_id)
    token = issue_account_token(user, AccountToken.Purpose.PASSWORD_RESET, timedelta(minutes=30))
    url = build_action_url(settings.PASSWORD_RESET_URL, token)
    send_mail(
        subject="Reset your password",
        message=(
            "Reset your password using this link:\n\n"
            f"{url}\n\n"
            "This link expires in 30 minutes. If you did not request a password reset, ignore this email."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )


@shared_task
def expire_old_data_exports():
    from django.utils import timezone
    from .models import DataExportRequest

    return DataExportRequest.objects.filter(
        status=DataExportRequest.Status.READY,
        expires_at__lt=timezone.now(),
    ).update(status=DataExportRequest.Status.EXPIRED)


@shared_task
def list_due_account_deletions():
    """Return due deletion request IDs for an operator-approved erasure job.

    The project intentionally separates scheduling from irreversible deletion so
    teams can review legal, billing, fraud, and audit obligations before hard
    delete/anonymization.
    """
    from django.utils import timezone
    from .models import AccountDeletionRequest

    return list(
        AccountDeletionRequest.objects.filter(
            status=AccountDeletionRequest.Status.CONFIRMED,
            scheduled_for__lte=timezone.now(),
        ).values_list("id", flat=True)
    )
