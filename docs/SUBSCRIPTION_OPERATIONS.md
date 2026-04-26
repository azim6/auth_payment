# v12 Subscription Operations and Usage Controls

v12 adds operational billing controls on top of the v10 billing foundation and v11 Stripe integration.
The goal is to let admins safely operate subscriptions while each application still consumes simple entitlements and usage limits.

## Main capabilities

- Plan changes through durable `SubscriptionChangeRequest` records.
- Quantity and seat-limit changes.
- Cancel at period end.
- Cancel immediately.
- Resume/reactivate subscription records.
- Trial extension.
- Grace-period extension for past-due customers.
- Usage metric catalog.
- Append-only usage records with optional idempotency keys.
- Organization usage summary endpoint.

## Subscription lifecycle model

Provider webhooks remain the source of truth for provider-owned subscriptions, but admin actions are recorded as explicit change requests.
This makes it easier to audit who changed a subscription and why.

For provider subscriptions, the manual change request should normally be mirrored to Stripe/Paddle in a future provider adapter before being marked applied.
For manual/free subscriptions, the included service can apply the change directly.

## Seat limits

`Subscription.seat_limit` is separate from provider quantity because not all prices map one-to-one to seats.
For simple team pricing, set `quantity == seat_limit`.
For custom contracts, leave provider quantity as the commercial billing quantity and set `seat_limit` to the contractual member limit.

## Usage records

Usage is append-only. Do not overwrite usage rows.

Recommended idempotency keys:

```text
<service>:<event-id>
store:order:ord_123
api:request-bucket:2026-04-24T15:00Z
social:scheduled-post:post_123
```

## Entitlements and limits

Usage metrics point to an entitlement key, such as:

```text
api.requests.monthly.max
store.products.max
social.accounts.max
blog.posts.max
```

Applications should check:

```text
GET /api/v1/billing/orgs/{slug}/entitlements/
GET /api/v1/billing/orgs/{slug}/usage/
```

## New endpoints

```text
GET  /api/v1/billing/subscription-changes/             staff only
POST /api/v1/billing/subscription-changes/             staff only
POST /api/v1/billing/subscription-changes/{id}/apply/  staff only
GET  /api/v1/billing/usage-metrics/                    staff only
POST /api/v1/billing/usage-metrics/                    staff only
GET  /api/v1/billing/usage-records/                    staff only
POST /api/v1/billing/usage-records/record/             authenticated billing managers
GET  /api/v1/billing/orgs/{slug}/usage/                billing managers
```

## Security notes

- Treat subscription changes as financial admin actions.
- Require MFA for staff/admin users before production use.
- Keep provider webhooks as the reconciliation source of truth.
- Use idempotency keys for usage events from distributed systems.
- Keep usage records immutable unless a formal correction workflow is added.
