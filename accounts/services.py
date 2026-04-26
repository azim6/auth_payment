import logging

from django.conf import settings

from .tasks import send_email_verification_task, send_password_reset_task

logger = logging.getLogger(__name__)


def queue_email_verification(user) -> None:
    if settings.ACCOUNT_EMAIL_DELIVERY == "sync":
        send_email_verification_task.run(str(user.pk))
        return
    send_email_verification_task.delay(str(user.pk))


def queue_password_reset(user) -> None:
    if settings.ACCOUNT_EMAIL_DELIVERY == "sync":
        send_password_reset_task.run(str(user.pk))
        return
    send_password_reset_task.delay(str(user.pk))
