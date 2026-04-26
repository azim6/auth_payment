# Django Auth Payment Core v43

Business-focused central authentication and payment backend for:

- ZATCA document generator
- Typing test
- Chat app
- Blog

This version defaults to a simplified production core. Advanced enterprise modules from earlier versions remain in the repository but are disabled by default.

## Default runtime profile

```env
AUTH_PAYMENT_PROFILE=business
AUTH_PAYMENT_ENABLE_ADVANCED_APPS=false
```

## Core enabled apps

- accounts
- billing
- admin_integration
- admin_console
- customer_portal
- notifications
- ops
- production_verification

## Seed business products

```bash
python manage.py migrate
python manage.py seed_business_products
```

## Admin Control Platform

The separate admin project should control this backend through secure APIs only. It should not connect directly to this database.

Recommended flow:

```text
admin.yourdomain.com -> admin-api.yourdomain.com -> auth/payment API -> database
```

See:

- `docs/BUSINESS_CORE_v43.md`
- `docs/ADMIN_INTEGRATION_CONTRACT_v39.md`
- `docs/PRODUCTION_VERIFICATION_v42.md`
- `docs/RELEASE_NOTES_v43.md`

# Django Auth Platform v33

Production-oriented central authentication, authorization, billing, payment-processing, developer-platform, compliance, operations, notification, observability, fraud/abuse, usage billing, and regional tax/pricing service for web, Android, Windows, and internal services such as blog, store, social media, and admin systems.

## Version

```text
Project: django-auth-platform
Version: 33.0.0
Base framework: Django 5.2 LTS
API style: Django REST Framework
Token auth: Simple JWT with refresh-token rotation and blacklist support
Web auth: Django secure HttpOnly session cookies
Database: PostgreSQL
Cache/broker: Redis
Background jobs: Celery
Deployment: Docker Compose + Caddy reverse proxy
```

## What v33 changes

- Switches project direction from feature expansion to completion/hardening
- Adds feature readiness matrix and completion policy
- Adds production MVP scope definition
- Adds cross-module integration map for auth, billing, admin, portal, ops, and compliance
- Adds validation scripts for repository structure, migrations, docs, and settings
- Adds release notes for v33 stabilization

## Quick start: local development

```bash
cp .env.example .env
docker compose up --build
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

Visit:

```text
http://localhost:8000/api/v1/health/
http://localhost:8000/admin/
```




### v7 privacy and compliance operations

```http
GET   /api/v1/privacy/preferences/
PATCH /api/v1/privacy/preferences/
GET   /api/v1/privacy/consents/
POST  /api/v1/privacy/consents/
GET   /api/v1/privacy/data-exports/
POST  /api/v1/privacy/data-exports/
GET   /api/v1/privacy/data-export-payload/
GET   /api/v1/privacy/account-deletion/
POST  /api/v1/privacy/account-deletion/
POST  /api/v1/privacy/account-deletion/confirm/
POST  /api/v1/privacy/account-deletion/cancel/
```

v7 adds privacy and compliance foundations suitable for production account systems: consent history, privacy preferences, data export requests, and staged account deletion. See `docs/PRIVACY_COMPLIANCE.md`.


### v6 device, token, and service-key operations

```http
GET  /api/v1/auth/sessions/devices/
POST /api/v1/auth/sessions/devices/{device_id}/revoke/
GET  /api/v1/auth/tokens/refresh-families/
POST /api/v1/auth/tokens/refresh-families/revoke-all/
POST /api/v1/service/credentials/{credential_id}/rotate/
POST /api/v1/service/credentials/{credential_id}/deactivate/
```

v6 adds operational controls needed before using the auth service across web, Android, Windows, and internal services. Web logins are recorded as session devices. JWT logins record refresh-token family metadata so users and admins can reason about active mobile/desktop credentials. Service credentials can now be rotated without creating a new service identity.

## Key API endpoints

### Health

```http
GET /api/v1/health/
```

### Account lifecycle

```http
POST /api/v1/auth/register/
POST /api/v1/auth/email/verify/resend/
POST /api/v1/auth/email/verify/confirm/
POST /api/v1/auth/password/reset/request/
POST /api/v1/auth/password/reset/confirm/
```

### JWT auth for Android, Windows, desktop, and API clients

```http
POST /api/v1/auth/token/
POST /api/v1/auth/token/refresh/
POST /api/v1/auth/logout/
```

### Web session auth for browser apps

```http
POST /api/v1/auth/session/login/
POST /api/v1/auth/session/logout/
GET  /api/v1/auth/session/status/
```

### MFA

```http
GET  /api/v1/auth/mfa/status/
POST /api/v1/auth/mfa/setup/start/
POST /api/v1/auth/mfa/setup/confirm/
POST /api/v1/auth/mfa/recovery-codes/regenerate/
POST /api/v1/auth/mfa/disable/
```

### OAuth/OIDC foundation

```http
GET  /api/v1/.well-known/openid-configuration
GET  /api/v1/oauth/jwks/
GET  /api/v1/oauth/authorize/
POST /api/v1/oauth/authorize/
POST /api/v1/oauth/token/
GET  /api/v1/oauth/clients/        # admin
POST /api/v1/oauth/clients/        # admin
```

### v5 security operations

```http
GET  /api/v1/audit/logs/           # admin
GET  /api/v1/oauth/tokens/         # admin
POST /api/v1/oauth/introspect/     # admin
POST /api/v1/oauth/revoke/         # admin
GET  /api/v1/service/credentials/  # admin
POST /api/v1/service/credentials/  # admin
POST /api/v1/service/token/        # service key -> service access token
```

## Service credentials

Create a service credential as an admin:

```http
POST /api/v1/service/credentials/
Authorization: Bearer admin-access-token
Content-Type: application/json

{
  "name": "blog-service",
  "scopes": "users:read tokens:introspect",
  "expires_at": "2027-01-01T00:00:00Z"
}
```

The response contains `raw_key` once. Store it in the target service secret manager. The database stores only a hash and key prefix.

Exchange the service key for a short-lived access token:

```http
POST /api/v1/service/token/
Content-Type: application/json

{
  "grant_type": "client_credentials",
  "service_key": "svc_...",
  "scope": "users:read"
}
```

## Token introspection and revocation

```http
POST /api/v1/oauth/introspect/
Authorization: Bearer admin-access-token
Content-Type: application/json

{
  "token": "access-or-refresh-token"
}
```

```http
POST /api/v1/oauth/revoke/
Authorization: Bearer admin-access-token
Content-Type: application/json

{
  "token": "access-or-refresh-token"
}
```

Refresh-token revocation also attempts to use the Simple JWT blacklist app. Access-token revocation is tracked in `OAuthTokenActivity`; downstream services should call introspection or validate against the auth service for high-risk actions.

## Production checklist

Before production:

```text
- Set a strong SECRET_KEY.
- Set DEBUG=False.
- Restrict ALLOWED_HOSTS.
- Set CSRF_TRUSTED_ORIGINS and CORS_ALLOWED_ORIGINS.
- Use PostgreSQL, not SQLite.
- Use HTTPS only.
- Use secure cookie settings.
- Configure SMTP.
- Configure backups for PostgreSQL.
- Rotate service credentials periodically.
- Review audit logs for suspicious activity.
```

## Upgrade notes

v6 includes migration `0006_sessiondevice_refreshtokenfamily.py`. Apply migrations after upgrading from v4:

```bash
python manage.py migrate
```

## v8 organization tenancy

v8 introduces organization/workspace support for B2B and multi-project deployments.

```http
POST /api/v1/orgs/
Authorization: Bearer user-access-token
Content-Type: application/json

{
  "name": "Acme Ltd",
  "slug": "acme",
  "plan": "team"
}
```

Invite a member:

```http
POST /api/v1/orgs/acme/invitations/
Authorization: Bearer owner-or-admin-access-token
Content-Type: application/json

{
  "email": "teammate@example.com",
  "role": "member",
  "expires_at": "2027-01-01T00:00:00Z"
}
```

Accept an invitation:

```http
POST /api/v1/orgs/invitations/accept/
Authorization: Bearer invited-user-access-token
Content-Type: application/json

{
  "token": "invite_..."
}
```

Create a tenant-scoped service credential:

```http
POST /api/v1/orgs/acme/service-credentials/
Authorization: Bearer owner-or-admin-access-token
Content-Type: application/json

{
  "name": "acme-store-sync",
  "scopes": "org:read members:read users:read"
}
```

The response contains the `raw_key` once. Store it outside the database.

## Upgrade notes for v8

v8 includes migration `0008_enterprise_tenancy.py`.

```bash
python manage.py migrate
```


## v9 authorization layer

Version 9 adds tenant-scoped RBAC, permission policies, role grants, access-check endpoints, and service-scope permission mapping. See `docs/AUTHORIZATION.md`.

## v10: Billing and payment-processing foundation

v10 adds a separate `billing` app that works with the auth/organization/RBAC system without storing payment data inside the core auth models.

Highlights:

- billable projects such as blog, store, social, API
- public/private/internal plans
- recurring, one-time, custom, and free prices
- organization/user billing customers
- admin-granted free/manual subscriptions
- plan-level and subscription-level entitlements
- invoice and payment transaction records
- idempotent provider webhook log
- staff APIs and Django admin for billing operations
- organization billing summary and entitlements endpoints

Apps should call `/api/v1/billing/orgs/{slug}/entitlements/` to decide feature access instead of checking provider billing status directly.

## v11 payment endpoints

```text
POST /api/v1/billing/checkout-sessions/create/
POST /api/v1/billing/portal-sessions/create/
POST /api/v1/billing/webhooks/stripe/
GET  /api/v1/billing/checkout-sessions/   staff only
GET  /api/v1/billing/portal-sessions/     staff only
```

Checkout and portal session creation uses tenant billing access checks. Staff users, tenant owners, and users with `billing.manage` may create payment sessions for the organization.

Stripe webhook processing is signature-verified and idempotent. Webhook payloads are stored in `BillingWebhookEvent` for operations, audit, and replay workflows.

See `docs/STRIPE_BILLING.md` for the v11 payment integration details.

## v12 subscription operations

v12 adds operational billing controls for production SaaS work:

- subscription change requests
- plan changes
- quantity/seat-limit changes
- cancel now / cancel at period end
- resume/reactivate
- trial and grace-period extensions
- usage metric catalog
- append-only usage records
- organization usage summary

See `docs/SUBSCRIPTION_OPERATIONS.md` for details.

## v13 invoicing, tax, refunds, and dunning

v13 adds the billing governance layer needed for production SaaS/payment operations:

- structured billing profiles
- customer tax IDs
- credit notes
- refund request review workflow
- dunning/collections cases
- invoice/credit-note sequence helpers
- staff-only billing governance APIs

See `docs/INVOICING_TAX_DUNNING.md`.

## v14 Revenue Automation

v14 adds a production billing growth layer while keeping billing separate from auth:

- Discounts and promotion codes
- Private organization-specific offers
- Discount redemption ledger with idempotency
- Add-ons for seats, quotas, one-time products, and future metered billing
- Add-on entitlements merged into product access
- Cached entitlement snapshots for product apps

See `docs/BILLING_REVENUE_AUTOMATION.md`.

## v15 reliability operations

This version adds production billing reliability features:

- transactional billing outbox
- provider sync health tracking
- webhook replay workflow
- entitlement change history
- outbox dispatch Celery task and management command

See `docs/BILLING_RELIABILITY_OPS.md` for the runbook and endpoints.

## v17 compliance governance

v17 adds a dedicated `compliance` app for production governance workflows that operate across auth, billing, tenants, and security operations:

- versioned policy documents
- user and organization policy acceptance ledger
- two-person admin approval requests
- audit export request tracking
- evidence packs for incidents, disputes, customer audits, and compliance reviews

See `docs/COMPLIANCE_GOVERNANCE.md` for endpoint and operational details.

## v18 operations/deployment maturity

v18 adds a separate `ops` app for production deployment and platform operations.

New capabilities:

```text
staff-only readiness checks
public liveness endpoint
public status endpoint
environment safety checks
service health check records
maintenance windows
backup snapshot metadata
restore run approval tracking
status incidents
release/version metadata
CI/CD healthcheck command
release metadata command
```

New endpoints:

```text
GET  /api/v1/ops/live/
GET  /api/v1/ops/status/
GET  /api/v1/ops/ready/                         staff only
GET  /api/v1/ops/environment-checks/            staff only
POST /api/v1/ops/environment-checks/refresh/    staff only
GET  /api/v1/ops/health-checks/                 staff only
POST /api/v1/ops/health-checks/refresh/         staff only
GET/POST /api/v1/ops/maintenance-windows/       staff only
GET/POST /api/v1/ops/backups/                   staff only
GET/POST /api/v1/ops/restores/                  staff only
GET/POST /api/v1/ops/incidents/                 staff only
GET/POST /api/v1/ops/releases/                  staff only
```

See `docs/OPERATIONS_DEPLOYMENT.md` for runbooks and operational guidance.

## v19 developer platform integrations

v19 adds a `developer_platform` app for connecting your central auth/billing platform to all first-party sites and clients:

- web app registrations
- Android app registrations
- Windows desktop app registrations
- service/CLI app registrations
- per-platform SDK token policies
- outbound webhook subscriptions
- webhook delivery logs
- integration audit events

See `docs/DEVELOPER_PLATFORM.md`.

## v21 observability

v21 adds a dedicated `observability` app for production monitoring and operational insight:

```text
structured application events
metric snapshots
request trace metadata
SLO definitions and snapshots
error-budget tracking fields
alert rules
alert incidents
observability heartbeat command
staff-only observability APIs
```

New endpoints:

```text
GET      /api/v1/observability/summary/
GET/POST /api/v1/observability/events/
GET/POST /api/v1/observability/metrics/
GET/POST /api/v1/observability/traces/
GET/POST /api/v1/observability/slos/
POST     /api/v1/observability/slos/{id}/calculate/
GET/POST /api/v1/observability/alert-rules/
POST     /api/v1/observability/alert-rules/{id}/evaluate/
GET      /api/v1/observability/alert-incidents/
POST     /api/v1/observability/alert-incidents/{id}/action/
```

See `docs/OBSERVABILITY.md`.

## v22 data governance

v22 adds a dedicated `data_governance` app for privacy and data lifecycle control across auth, billing, notifications, observability, and future product apps:

```text
data category catalog
data asset inventory
PII/payment data classification
retention policies
legal holds
data subject request workflow
retention job planning and dry runs
append-only anonymization record metadata
inventory snapshots for evidence packs
```

New endpoints:

```text
GET      /api/v1/data-governance/summary/
GET/POST /api/v1/data-governance/categories/
GET/POST /api/v1/data-governance/assets/
GET/POST /api/v1/data-governance/retention-policies/
GET/POST /api/v1/data-governance/legal-holds/
POST     /api/v1/data-governance/legal-holds/{id}/release/
GET/POST /api/v1/data-governance/subject-requests/
POST     /api/v1/data-governance/subject-requests/{id}/action/
GET/POST /api/v1/data-governance/retention-jobs/
POST     /api/v1/data-governance/retention-jobs/plan/
POST     /api/v1/data-governance/retention-jobs/{id}/run/
GET      /api/v1/data-governance/anonymization-records/
GET/POST /api/v1/data-governance/inventory-snapshots/
```

See `docs/DATA_GOVERNANCE.md`.

## v23 fraud and abuse controls

v23 adds a separate `fraud_abuse` app for production risk controls across auth, billing, notifications, platform APIs, and first-party apps.

Highlights:

- hashed device fingerprint registry
- IP reputation records
- append-only abuse signals
- velocity rules and velocity event recording
- abuse investigation cases
- payment-risk review queue
- signal promotion into security operations
- safe enforcement through account restrictions

Primary route:

```text
/api/v1/fraud-abuse/
```

See `docs/FRAUD_ABUSE.md`.

## v24 Admin console foundation

v24 adds an API-first staff console layer for support, billing, security, compliance, and operations workflows. It is separate from Django's built-in `/admin/` and is designed for safer product-operator workflows.

```http
GET  /api/v1/admin-console/summary/
POST /api/v1/admin-console/snapshots/create/
GET/POST /api/v1/admin-console/widgets/
GET/POST /api/v1/admin-console/views/
GET/POST /api/v1/admin-console/tasks/
POST /api/v1/admin-console/tasks/{id}/action/
GET/POST /api/v1/admin-console/bulk-actions/
POST /api/v1/admin-console/bulk-actions/{id}/action/
GET/POST /api/v1/admin-console/notes/
GET /api/v1/admin-console/users/{user_id}/overview/
GET /api/v1/admin-console/orgs/{slug}/overview/
```

See `docs/ADMIN_CONSOLE.md` for the operator workflow model and security guidance.

## v25 Customer self-service portal

v25 adds a separate `customer_portal` app for end-user and organization-owner workflows. It complements the staff-only `admin_console` app added in v24.

Added capabilities:

```text
customer profile settings
organization overview for members
portal organization bookmarks
customer-visible billing summary
customer-managed API keys with hashed storage
customer support requests
customer activity log
portal-specific production documentation
```

Main routes:

```text
/api/v1/portal/summary/
/api/v1/portal/profile/settings/
/api/v1/portal/organizations/
/api/v1/portal/billing/
/api/v1/portal/api-keys/
/api/v1/portal/support-requests/
/api/v1/portal/activity/
```

See `docs/CUSTOMER_PORTAL.md` for implementation and security notes.

## v27 Identity Hardening

Version 26 adds a dedicated `identity_hardening` app for modern authentication assurance across web, Android, Windows, and service clients. It introduces passkey/WebAuthn metadata scaffolding, short-lived passkey challenges, trusted-device records, step-up authentication sessions, recovery policies, and an append-only identity assurance event ledger.

Important production note: v27 stores the data model and API flow needed for passkeys, but real WebAuthn attestation/assertion verification must be wired to a reviewed WebAuthn implementation before accepting production passkey credentials. Keep relying on password + TOTP MFA until that verification layer is integrated and tested.

New route prefix: `/api/v1/identity/`.


## v27 Enterprise SSO readiness

Added a dedicated `enterprise_sso` app for SAML/OIDC identity provider records, verified domains, SSO policies, JIT provisioning rules, SSO routing, and login event ledgers. See `docs/ENTERPRISE_SSO.md`.

### v28 SCIM provisioning

```http
GET/POST /api/v1/scim/applications/
POST     /api/v1/scim/applications/{id}/activate/
POST     /api/v1/scim/applications/{id}/rotate-token/
GET/POST /api/v1/scim/directory-users/
GET/POST /api/v1/scim/directory-groups/
GET/POST /api/v1/scim/deprovisioning-policies/
GET/POST /api/v1/scim/sync-jobs/
GET      /api/v1/scim/events/
GET      /api/v1/scim/summary/
POST     /api/v1/scim/v2/{application_id}/Users/upsert/
POST     /api/v1/scim/v2/{application_id}/Users/deactivate/
POST     /api/v1/scim/v2/{application_id}/Groups/upsert/
```

v28 adds enterprise directory lifecycle automation for customers using Okta, Microsoft Entra ID/Azure AD, Google Workspace, OneLogin, or custom HRIS bridges. See `docs/SCIM_PROVISIONING.md`.

## v29 OIDC provider hardening

Version 29 adds a dedicated `oidc_provider` app for JWKS lifecycle management, scope and claim catalogs, consent grants, client trust profiles, refresh-token policy records, token-exchange policies, and discovery metadata snapshots. See `docs/OIDC_PROVIDER_HARDENING.md`.

## v30 SDK and Developer Experience

v30 adds first-party client SDK skeletons and an SDK registry API:

```text
sdks/typescript
sdks/android-kotlin
sdks/windows-dotnet
api/v1/sdk/
```

See `docs/SDK_DEVELOPER_EXPERIENCE.md` for token-storage guidance, SDK release governance, telemetry boundaries, and compatibility policy.

## v31 Usage-Based Billing

Version 31 adds a dedicated `usage_billing` app for metered usage across all first-party projects. It supports meter definitions, idempotent usage ingestion, aggregation windows, rated invoice-ready usage lines, prepaid/manual credits, and reconciliation metadata.

Product apps should ingest usage events only. Billing jobs aggregate, rate, finalize, and reconcile before provider export.

Key route prefix:

```text
/api/v1/usage-billing/
```

## v33 completion direction

v33 freezes broad feature expansion. The project now prioritizes completing and hardening the features already present: auth, billing, tenancy/RBAC, admin console, customer portal, provider integrations, compliance, operations, notifications, observability, fraud controls, usage billing, and tax/pricing.

Recommended next work is documented in:

- `docs/FEATURE_READINESS_MATRIX.md`
- `docs/PRODUCTION_MVP_SCOPE.md`
- `docs/API_INTEGRATION_MAP.md`
- `docs/UPGRADE_POLICY.md`

Useful validation helpers:

```bash
make validate-structure
make module-inventory
```

## v34 completion update

v34 does not add a new feature area. It finishes key payment-processing gaps in the existing billing module: Stripe webhook state sync, entitlement recalculation, provider event outbox emission, subscription operation sync, refund processing, dunning-case updates, and billing readiness checks.

See `docs/PAYMENT_COMPLETION_v34.md` and `docs/RELEASE_NOTES_v34.md`.

## v35 auth and identity completion

v35 does not add a new feature area. It completes part of the existing auth stack by adding a staff-only auth readiness report and a deployment acceptance checklist for web, Android, Windows, API, and internal-service auth flows.

New endpoint:

```text
GET /api/v1/auth/readiness/
```

See `docs/AUTH_COMPLETION_v35.md` and `docs/RELEASE_NOTES_v35.md`.

## v36 Tenant authorization completion

This release adds a staff-only tenant/RBAC readiness report at `GET /api/v1/tenancy/readiness/` and documents the production access-review checklist in `docs/TENANT_AUTHORIZATION_COMPLETION_v36.md`.

## v37 Admin and customer portal completion

v37 stays in completion mode. It adds staff-only readiness reports for the admin console and customer portal, plus support-request escalation into operator tasks.

New endpoints:

```text
GET  /api/v1/admin-console/readiness/
GET  /api/v1/portal/readiness/
POST /api/v1/portal/support-requests/{id}/escalate/
```

See `docs/ADMIN_PORTAL_COMPLETION_v37.md` and `docs/RELEASE_NOTES_v37.md`.

## v38 Notifications and observability completion

v38 stays in completion mode. It adds staff-only readiness reports for notification delivery and observability so operators can verify providers, templates, delivery queues, SLOs, traces, metrics, and alert rules before launch.

```http
GET /api/v1/notifications/readiness/
GET /api/v1/observability/readiness/
```

See `docs/NOTIFICATIONS_OBSERVABILITY_COMPLETION_v38.md` and `docs/RELEASE_NOTES_v38.md`.

## v39 Admin integration contract

v39 stays in completion mode and makes the Auth + Payment Platform ready to be controlled by a separate admin-control project. It adds the `admin_integration` app, signed service-to-service request verification, admin service credentials, request audit middleware, a stable admin API contract catalogue, and a staff-only readiness endpoint.

New API group:

```text
/api/v1/admin-integration/
```

See `docs/ADMIN_INTEGRATION_CONTRACT_v39.md` and `docs/RELEASE_NOTES_v39.md`.

## v40 Production boot validation

Run these before connecting the separate Admin Control Platform to production:

```bash
make production-bootstrap
make production-preflight
make smoke-http BASE_URL=https://auth.example.com
```

The Admin Control Platform should also call:

```http
GET /api/v1/ops/production-validation/
GET /api/v1/admin-integration/readiness/
```

## v42 production verification

```bash
python manage.py production_verify
python manage.py production_verify --persist
make production-verify
make admin-contract-smoke BASE_URL=https://auth.yourdomain.com ADMIN_TOKEN=...
```

The separate Admin Control Platform should call:

```http
GET /api/v1/production-verification/verify/
```

## v44 Business Rules + Product Access Engine

v44 adds a default-enabled `business_rules` app for ZATCA document generator, typing test, chat app, and blog.

Product apps should call:

```http
POST /api/v1/business/access-check/
```

before performing limited or paid actions such as generating a ZATCA document, starting a premium typing test, uploading a chat file, or writing a blog post.

Seed business products and plans with:

```bash
python manage.py seed_business_products
```

See `docs/BUSINESS_RULES_v44.md` for the integration contract.
