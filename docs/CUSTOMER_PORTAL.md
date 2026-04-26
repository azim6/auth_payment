# v25 Customer Self-Service Portal

v25 adds an API-first customer portal layer for account holders and organization owners. It is separate from the staff/admin console and is designed for web, Android, and Windows clients.

## Responsibilities

The `customer_portal` app exposes customer-safe workflows:

- profile and portal preferences
- organization membership overview
- pinned organization/workspace navigation
- customer-visible billing summary
- customer-managed API keys
- customer support requests
- customer-visible activity feed

The portal must never expose raw payment-provider data, staff-only notes, hashed secrets, internal risk scores, or cross-tenant records.

## Key endpoints

```text
GET      /api/v1/portal/summary/
GET/PATCH /api/v1/portal/profile/settings/
GET      /api/v1/portal/organizations/
GET      /api/v1/portal/organizations/{slug}/overview/
GET/POST /api/v1/portal/bookmarks/
GET/POST /api/v1/portal/api-keys/
POST     /api/v1/portal/api-keys/{id}/revoke/
GET      /api/v1/portal/billing/
GET/POST /api/v1/portal/support-requests/
POST     /api/v1/portal/support-requests/{id}/close/
GET      /api/v1/portal/activity/
```

## API key security

Customer portal API keys are hashed at rest. The raw key is returned only once when created. The key format uses the `cpak_` prefix and supports scope restrictions:

```text
profile:read
profile:write
org:read
org:write
billing:read
billing:write
privacy:read
privacy:write
support:write
```

Use these keys only for customer-owned integrations. Internal service automation should continue to use service credentials from the auth/tenant/developer-platform layers.

## Billing boundary

The portal summarizes billing records already owned by the billing app. Payment method updates and hosted payment actions should still happen through provider customer portal flows, such as Stripe Customer Portal, rather than collecting card data in this app.

## Mobile and desktop clients

Android and Windows clients should use the same endpoints with JWT authentication. Store refresh tokens in OS-provided secure storage and never store portal API keys in plain text.

## Operator workflow

Customer support requests created through the portal can be linked to `admin_console.OperatorTask` records by a later escalation workflow. The portal itself only creates customer-originated requests and does not grant staff privileges.
