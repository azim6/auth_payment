from .base import *  # noqa: F403

DEBUG = False
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
AXES_ENABLED = False
ACCOUNT_EMAIL_DELIVERY = "sync"
FRONTEND_BASE_URL = "http://testserver"
EMAIL_VERIFICATION_URL = "http://testserver/verify-email"
PASSWORD_RESET_URL = "http://testserver/reset-password"
CELERY_TASK_ALWAYS_EAGER = True
