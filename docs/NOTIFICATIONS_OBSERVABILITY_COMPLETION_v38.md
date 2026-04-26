# v38 Notifications and Observability Completion

v38 keeps the project in completion mode. It does not add a new product area; it finishes the operational checks around the existing notifications and observability modules.

## Goals

- Confirm notification delivery is safe to operate before production launch.
- Confirm observability has enough telemetry, SLOs, metrics, traces, and alerts to support auth and billing operations.
- Provide staff-only readiness endpoints that can be wired into the admin console or deployment checklist.

## Notification readiness

Endpoint:

```http
GET /api/v1/notifications/readiness/
```

The report checks:

- at least one active notification provider exists
- at least one active email provider exists
- active templates exist
- required account/security/billing/compliance email templates exist
- due pending deliveries are not piling up
- failed deliveries are not accumulating
- dead-letter deliveries require operator review
- queued events due for dispatch are visible

The readiness report is intentionally metadata-only. Recipient addresses, push tokens, and secrets remain hashed or outside the database.

## Observability readiness

Endpoint:

```http
GET /api/v1/observability/readiness/
```

The report checks:

- application events are being recorded
- metric snapshots are being recorded
- trace samples are being recorded
- active SLOs exist
- recent SLO snapshots exist
- active alert rules exist
- no open critical alerts exist

## Production acceptance checklist

Before launch, operators should confirm:

1. Notification readiness status is `ready` or only contains accepted warnings.
2. Observability readiness status is `ready` or only contains accepted warnings.
3. Security, billing, account, and compliance notification templates are active.
4. Dead-letter deliveries are zero or have documented owner review.
5. Critical SLOs exist for login, token refresh, checkout, webhook handling, and entitlement resolution.
6. Critical alert routing is connected to an on-call process.

## Completion-mode policy

v38 closes readiness gaps only. Provider-specific notification sending, external APM integrations, and advanced alert routing should be added only when a real provider is selected.
