# v10 Billing and Entitlements

v10 adds a separate `billing` Django app that integrates with the existing auth, organization, RBAC, service credential, and audit foundations without mixing payment state into core authentication tables.

## Design

Auth owns identity and access:

- users, sessions, MFA, OAuth/OIDC clients
- organizations and memberships
- tenant-scoped RBAC
- audit logs and service credentials

Billing owns commerce state:

- billable projects such as `blog`, `store`, `social`, or `api`
- plans and prices
- custom/manual pricing
- organization/user billing customers
- free/manual subscriptions
- invoices and payment transactions
- webhook event audit logs
- effective entitlements

## Core models

- `Project`: product/project that can have specific plans.
- `Plan`: public/private/internal package.
- `Price`: recurring, one-time, or custom/manual price.
- `BillingCustomer`: linked to exactly one organization or one user.
- `Subscription`: active/trial/free/past_due/cancelled subscription.
- `Entitlement`: plan or subscription-level feature flag/limit.
- `Invoice`: normalized invoice record from manual or provider systems.
- `PaymentTransaction`: normalized payment attempt/settlement record.
- `BillingWebhookEvent`: idempotent provider webhook store.

## Admin workflows

The admin can:

- create a project-specific plan, for example `store-pro` or `blog-enterprise`
- create free/internal/private plans
- set custom prices for special customers
- manually grant a free subscription to an organization
- add subscription-level entitlement overrides
- inspect invoices, payment records, and webhook events

## API routes

Base path: `/api/v1/billing/`

Public:

- `GET public/plans/`

Staff/admin:

- `GET/POST projects/`
- `GET/PATCH projects/{code}/`
- `GET/POST plans/`
- `GET/PATCH plans/{code}/`
- `GET/POST prices/`
- `GET/POST entitlements/`
- `GET customers/`
- `GET subscriptions/`
- `POST subscriptions/manual-grant/`
- `GET invoices/`
- `GET payments/`
- `GET webhooks/events/`

Organization billing:

- `GET orgs/{slug}/summary/`
- `GET orgs/{slug}/entitlements/`

## Entitlements pattern

Applications should not talk directly to Stripe/Paddle/etc. They should ask the platform for entitlements:

```json
{
  "features": {
    "store.products.max": 500,
    "store.enabled": true,
    "blog.posts.max": 1000,
    "api_access.enabled": true
  }
}
```

This lets auth, billing, and all projects work together while keeping provider-specific payment details isolated.

## Provider integration

v10 is provider-neutral. It is ready for Stripe, Paddle, Lemon Squeezy, or manual/offline billing.

Recommended next steps:

- v11: Stripe checkout, customer portal, signed webhook processing
- v12: Paddle/Lemon Squeezy merchant-of-record option
- v13: usage-based metering and quota enforcement
- v14: tax, invoice PDF, dunning and failed-payment recovery

## Security notes

- Never store raw card data.
- Use payment provider hosted checkout/customer portal where possible.
- Verify webhook signatures before mutating subscriptions.
- Store every webhook event idempotently.
- Treat subscription state as derived from provider webhooks or explicit admin action.
- Use entitlements for product decisions, not raw subscription status.

## v11 payment-provider integration

v11 adds Stripe checkout, customer portal sessions, webhook signature verification, and provider event processing while preserving the provider-neutral billing data model introduced in v10.

New operational records:

- `CheckoutSession`
- `CustomerPortalSession`

New endpoints:

```text
POST /api/v1/billing/checkout-sessions/create/
POST /api/v1/billing/portal-sessions/create/
POST /api/v1/billing/webhooks/stripe/
GET  /api/v1/billing/checkout-sessions/        staff only
GET  /api/v1/billing/portal-sessions/          staff only
```

The checkout and portal creation endpoints require tenant billing permission. The webhook endpoint is unauthenticated but must pass provider signature verification.
