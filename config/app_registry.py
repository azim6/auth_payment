"""Application registry for the business-focused auth/payment platform.

The repository contains several advanced modules from earlier platform experiments.  For
X Coder's current business apps (ZATCA document generator, typing test, chat app,
and blog), the default runtime profile intentionally enables only the compact core.
Advanced apps remain available for later activation but are disabled by default.
"""

DJANGO_CORE_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "corsheaders",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "drf_spectacular",
    "axes",
]

# Required for the real business: central auth, billing/payment, admin-control
# integration, customer self-service, basic notifications, and production checks.
BUSINESS_CORE_APPS = [
    "accounts",
    "billing",
    "business_rules",
    "admin_integration",
    "admin_console",
    "customer_portal",
    "notifications",
    "observability",
    "ops",
    "production_verification",
    "security_ops",
]

# Useful later, but not needed for the current ZATCA/typing/chat/blog launch.
OPTIONAL_ADVANCED_APPS = [
    "compliance",
    "developer_platform",
    "data_governance",
    "fraud_abuse",
    "identity_hardening",
    "enterprise_sso",
    "scim_provisioning",
    "oidc_provider",
    "sdk_registry",
    "usage_billing",
    "tax_pricing",
]

# Public URL prefixes owned by apps.  config.urls uses this registry so disabled
# apps do not get imported at runtime.
APP_URL_PREFIXES = {
    "accounts": "api/v1/",
    "billing": "api/v1/billing/",
    "business_rules": "api/v1/business/",
    "admin_integration": "api/v1/admin-integration/",
    "admin_console": "api/v1/admin-console/",
    "customer_portal": "api/v1/portal/",
    "notifications": "api/v1/notifications/",
    "ops": "api/v1/ops/",
    "production_verification": "api/v1/production-verification/",
    "security_ops": "api/v1/security/",
    "compliance": "api/v1/compliance/",
    "developer_platform": "api/v1/platform/",
    "observability": "api/v1/observability/",
    "data_governance": "api/v1/data-governance/",
    "fraud_abuse": "api/v1/fraud-abuse/",
    "identity_hardening": "api/v1/identity/",
    "enterprise_sso": "api/v1/enterprise-sso/",
    "scim_provisioning": "api/v1/scim/",
    "oidc_provider": "api/v1/oidc/",
    "sdk_registry": "api/v1/sdk/",
    "usage_billing": "api/v1/usage-billing/",
    "tax_pricing": "api/v1/tax-pricing/",
}

BUSINESS_PRODUCT_CODES = ["zatca", "typing", "chat", "blog"]

BUSINESS_ENTITLEMENT_KEYS = {
    "zatca": [
        "zatca.enabled",
        "zatca.documents_per_month",
        "zatca.templates_premium",
        "zatca.api_access",
    ],
    "typing": [
        "typing.enabled",
        "typing.tests_per_day",
        "typing.premium_tests",
        "typing.analytics",
    ],
    "chat": [
        "chat.enabled",
        "chat.messages_per_day",
        "chat.file_upload",
        "chat.history_days",
    ],
    "blog": [
        "blog.enabled",
        "blog.can_comment",
        "blog.can_write",
        "blog.manage_posts",
    ],
}


def build_installed_apps(enable_advanced: bool = False) -> list[str]:
    """Return the installed app list for the selected deployment profile."""
    apps = DJANGO_CORE_APPS + THIRD_PARTY_APPS + BUSINESS_CORE_APPS
    if enable_advanced:
        apps += OPTIONAL_ADVANCED_APPS
    return apps
