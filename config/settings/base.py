from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DEBUG=(bool, False),
)

env_file = BASE_DIR / ".env"
if env_file.exists():
    environ.Env.read_env(env_file)

SECRET_KEY = env("SECRET_KEY", default="unsafe-dev-secret-change-me")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

from config.app_registry import build_installed_apps

AUTH_PAYMENT_PROFILE = env("AUTH_PAYMENT_PROFILE", default="business")
AUTH_PAYMENT_ENABLE_ADVANCED_APPS = env.bool("AUTH_PAYMENT_ENABLE_ADVANCED_APPS", default=False)
INSTALLED_APPS = build_installed_apps(enable_advanced=AUTH_PAYMENT_ENABLE_ADVANCED_APPS)

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "admin_integration.middleware.AdminOriginAuditMiddleware",
    "axes.middleware.AxesMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": env.db("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}")
}
DATABASES["default"]["CONN_MAX_AGE"] = 60

AUTH_USER_MODEL = "accounts.User"
AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
]

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 12}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/hour",
        "user": "1000/hour",
        "auth": "20/minute",
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=10),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=14),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "AUTH_HEADER_TYPES": ("Bearer",),
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Django Auth Platform API",
    "DESCRIPTION": "Central authentication and user API for web, Android, Windows, and service clients.",
    "VERSION": "44.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

REDIS_URL = env("REDIS_URL", default="redis://localhost:6379/0")
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
    }
}

CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60

CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

SESSION_COOKIE_NAME = "auth_sessionid"
SESSION_COOKIE_DOMAIN = env("SESSION_COOKIE_DOMAIN", default=None)
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_NAME = "auth_csrftoken"
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = "Lax"

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env("EMAIL_HOST", default="localhost")
EMAIL_PORT = env.int("EMAIL_PORT", default=25)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=False)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="no-reply@example.com")
SERVER_EMAIL = env("SERVER_EMAIL", default=DEFAULT_FROM_EMAIL)

AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 1
AXES_LOCKOUT_PARAMETERS = [["username", "ip_address"]]
AXES_RESET_ON_SUCCESS = True

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "{levelname} {asctime} {name} {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "verbose"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
}

ACCOUNT_EMAIL_DELIVERY = env("ACCOUNT_EMAIL_DELIVERY", default="celery")  # celery|sync
FRONTEND_BASE_URL = env("FRONTEND_BASE_URL", default="http://localhost:3000")
EMAIL_VERIFICATION_URL = env("EMAIL_VERIFICATION_URL", default=f"{FRONTEND_BASE_URL}/verify-email")
PASSWORD_RESET_URL = env("PASSWORD_RESET_URL", default=f"{FRONTEND_BASE_URL}/reset-password")

MFA_TOTP_ISSUER = env("MFA_TOTP_ISSUER", default="Django Auth Platform")

OIDC_ISSUER = env("OIDC_ISSUER", default="http://localhost:8000")
OIDC_AUTHORIZATION_CODE_LIFETIME_MINUTES = env.int("OIDC_AUTHORIZATION_CODE_LIFETIME_MINUTES", default=5)

DATA_EXPORT_EXPIRY_DAYS = env.int("DATA_EXPORT_EXPIRY_DAYS", default=7)
ACCOUNT_DELETION_CONFIRM_WINDOW_HOURS = env.int("ACCOUNT_DELETION_CONFIRM_WINDOW_HOURS", default=24)
ACCOUNT_DELETION_GRACE_DAYS = env.int("ACCOUNT_DELETION_GRACE_DAYS", default=30)

# v11 payment-provider integration. Keep provider secrets in environment variables only.
BILLING_PROVIDER = env("BILLING_PROVIDER", default="stripe")
STRIPE_SECRET_KEY = env("STRIPE_SECRET_KEY", default="")
STRIPE_WEBHOOK_SECRET = env("STRIPE_WEBHOOK_SECRET", default="")

APP_VERSION = env("APP_VERSION", default="44.0.0")
OPERATIONS_PUBLIC_STATUS_ENABLED = env.bool("OPERATIONS_PUBLIC_STATUS_ENABLED", default=True)
BACKUP_STORAGE_BASE_URI = env("BACKUP_STORAGE_BASE_URI", default="")
MAINTENANCE_BYPASS_HEADER = env("MAINTENANCE_BYPASS_HEADER", default="X-Maintenance-Bypass")

# v20 notification infrastructure. Provider secrets belong in environment variables or a vault.
NOTIFICATION_DELIVERY_MODE = env("NOTIFICATION_DELIVERY_MODE", default="log")  # log|disabled|provider

# v23 fraud and abuse controls. External reputation feeds should be ingested by scheduled jobs, not request paths.
FRAUD_ABUSE_ENFORCEMENT_MODE = env("FRAUD_ABUSE_ENFORCEMENT_MODE", default="manual")  # manual|challenge|restrict

# v33 completion policy. These flags help teams separate production-critical modules
# from enterprise/advanced modules while keeping all code available for gradual hardening.
PLATFORM_FEATURE_COMPLETION_MODE = env("PLATFORM_FEATURE_COMPLETION_MODE", default="stabilize")
PRODUCTION_MVP_APPS = env.list(
    "PRODUCTION_MVP_APPS",
    default=[
        "accounts",
        "billing",
        "security_ops",
        "ops",
        "admin_console",
        "customer_portal",
        "notifications",
        "observability",
        "production_verification",
    ],
)
ADVANCED_APPS = env.list(
    "ADVANCED_APPS",
    default=[
        "compliance",
        "data_governance",
        "fraud_abuse",
        "identity_hardening",
        "enterprise_sso",
        "scim_provisioning",
        "oidc_provider",
        "sdk_registry",
        "usage_billing",
        "tax_pricing",
        "admin_integration",
        "developer_platform",
    ],
)

ADMIN_INTEGRATION_MAX_CLOCK_SKEW_SECONDS = env.int("ADMIN_INTEGRATION_MAX_CLOCK_SKEW_SECONDS", default=300)

# v40 production boot validation controls. These are used by ops readiness
# commands and the separate Admin Control Platform before production rollout.
PRODUCTION_BOOT_VALIDATION_REQUIRED = env.bool("PRODUCTION_BOOT_VALIDATION_REQUIRED", default=True)
PRODUCTION_BOOT_EXPECTED_HOSTS = env.list("PRODUCTION_BOOT_EXPECTED_HOSTS", default=[])
PRODUCTION_BOOT_EXPECTED_ORIGINS = env.list("PRODUCTION_BOOT_EXPECTED_ORIGINS", default=[])
PRODUCTION_BOOT_STRICT_OPTIONALS = env.bool("PRODUCTION_BOOT_STRICT_OPTIONALS", default=False)

PRODUCTION_VERIFICATION_REQUIRED_APPS = ["accounts", "billing", "admin_integration", "ops"]
PRODUCTION_VERIFICATION_EXPERIMENTAL_APPS = ["enterprise_sso", "scim_provisioning", "usage_billing", "tax_pricing"]

# Business-specific app identity for ZATCA, typing test, chat, and blog.
BUSINESS_PRODUCT_CODES = env.list("BUSINESS_PRODUCT_CODES", default=["zatca", "typing", "chat", "blog"])
ADMIN_CONTROL_ORIGINS = env.list("ADMIN_CONTROL_ORIGINS", default=[])
ADMIN_CONTROL_SERVICE_NAME = env("ADMIN_CONTROL_SERVICE_NAME", default="admin-control-platform")
