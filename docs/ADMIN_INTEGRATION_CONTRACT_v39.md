# v39 Admin Integration Contract

This document defines how the separate Admin Control Platform should control the Auth + Payment Platform.

## Boundary

The separate admin project must never connect directly to the auth/payment database. The allowed path is:

```text
admin frontend -> admin backend API -> signed Auth/Payment API calls -> Auth/Payment database
```

The Auth + Payment Platform remains the source of truth for users, organizations, roles, subscriptions, payments, entitlements, security restrictions, audit logs, and readiness status.

## New v39 API group

```http
GET  /api/v1/admin-integration/readiness/
GET  /api/v1/admin-integration/credentials/
POST /api/v1/admin-integration/credentials/
POST /api/v1/admin-integration/credentials/{id}/rotate/
POST /api/v1/admin-integration/credentials/{id}/deactivate/
GET  /api/v1/admin-integration/scopes/
GET  /api/v1/admin-integration/contract/
GET  /api/v1/admin-integration/request-audits/
POST /api/v1/admin-integration/verify-signed-request/
```

Staff users create an admin service credential once, then copy the returned API key and signing secret into the separate admin backend secret store.

## Required signed request headers

Every admin-origin request should include:

```http
X-Admin-Service-Key: adm_...
X-Admin-Timestamp: 1760000000
X-Admin-Nonce: unique-per-request
X-Admin-Signature: hmac-sha256-hex
```

Canonical request string:

```text
METHOD
PATH
TIMESTAMP
NONCE
SHA256_BODY_HEX
```

The HMAC is computed with the admin service credential's signing secret.

## Stable contract endpoints

The API contract endpoint returns stable endpoints the admin project may consume, including:

```http
GET /api/v1/auth/readiness/
GET /api/v1/tenancy/readiness/
GET /api/v1/billing/readiness/
GET /api/v1/admin-console/readiness/
GET /api/v1/portal/readiness/
GET /api/v1/notifications/readiness/
GET /api/v1/observability/readiness/
GET /api/v1/ops/ready/
GET /api/v1/admin-console/users/{user_id}/overview/
GET /api/v1/admin-console/orgs/{slug}/overview/
POST /api/v1/security/restrictions/
POST /api/v1/billing/entitlement-snapshots/recalculate-with-log/
```

## Security requirements

Use all of these together:

- VPN, Cloudflare Access, or private network access for admin API traffic.
- IP allowlist at proxy level and optionally per credential.
- HMAC request signing.
- Short timestamp skew, default 300 seconds.
- One nonce per request from the admin backend.
- Rotatable admin service credentials.
- Least-privilege admin scopes.
- Audit every admin-origin request.
- Two-person approval for destructive or high-risk actions.

## Important production note

v39 includes a direct signing secret field so the scaffold can verify HMAC requests. In production, replace this field with encrypted field storage or KMS-backed secret retrieval before launch.
