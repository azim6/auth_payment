# v43 Business Core Upgrade

This release trims the platform for the actual business apps:

- ZATCA document generator
- Typing test
- Chat app
- Blog

The project is still an auth + payment backend, but it now defaults to a compact runtime profile instead of enabling every advanced enterprise module.

## Default enabled apps

The default `business` profile enables:

- `accounts` - users, sessions, JWT, email verification, password reset, MFA/recovery-code foundation, organizations, memberships
- `billing` - projects, plans, prices, subscriptions, Stripe/manual payment records, entitlements
- `admin_integration` - secure integration point for the separate Admin Control Platform
- `admin_console` - API surface for admin dashboards and operator workflows
- `customer_portal` - API surface for customer self-service
- `notifications` - basic notification/event delivery records
- `ops` - health/readiness/status endpoints
- `production_verification` - deployment verification checks

## Disabled by default

These advanced modules remain in the repository but are not installed unless `AUTH_PAYMENT_ENABLE_ADVANCED_APPS=true`:

- enterprise SSO / SAML
- SCIM provisioning
- advanced OIDC provider hardening
- SDK registry
- usage billing
- tax/multi-currency regional pricing
- data governance
- compliance governance
- fraud/abuse investigation suite
- observability suite
- developer platform registry
- identity hardening/passkey scaffolding

This avoids unnecessary migrations, API routes, and operational complexity during the first production launch.

## Product entitlement model

The business apps should ask this backend for access and limits instead of hardcoding plan logic.

Example keys:

```text
zatca.enabled
zatca.documents_per_month
zatca.templates_premium
zatca.api_access

typing.enabled
typing.tests_per_day
typing.premium_tests
typing.analytics

chat.enabled
chat.messages_per_day
chat.file_upload
chat.history_days

blog.enabled
blog.can_comment
blog.can_write
blog.manage_posts
```

## Seed default products/plans

After migrations:

```bash
python manage.py seed_business_products
```

This creates baseline projects, free plans, paid plans, prices, and entitlements for ZATCA, typing, chat, and blog.

## Admin Control Platform integration

The separate admin project should call this backend through the `admin_integration` API and must not connect directly to the auth/payment database.

Recommended pattern:

```text
admin frontend -> admin backend -> auth/payment API -> auth/payment database
```

The admin project should control:

- users
- organizations
- subscriptions
- free/custom plans
- payment state
- entitlement overrides
- project access limits
- security restrictions

## Runtime profile settings

```env
AUTH_PAYMENT_PROFILE=business
AUTH_PAYMENT_ENABLE_ADVANCED_APPS=false
BUSINESS_PRODUCT_CODES=zatca,typing,chat,blog
ADMIN_CONTROL_ORIGINS=https://admin.yourdomain.com,https://admin-api.yourdomain.com
```

To enable the old advanced modules later:

```env
AUTH_PAYMENT_ENABLE_ADVANCED_APPS=true
```

Do that only after reviewing migrations, URLs, permissions, and operational readiness.
