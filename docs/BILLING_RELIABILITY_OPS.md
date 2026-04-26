# v15 Billing Reliability Operations

v15 adds reliability controls around the v10-v14 billing system so payment state can be audited, replayed, reconciled, and safely delivered to product apps.

## Main additions

- `BillingOutboxEvent`: transactional outbox for reliable billing side effects.
- `ProviderSyncState`: health/cursor state for provider reconciliation jobs.
- `WebhookReplayRequest`: auditable operator replay workflow for webhook events.
- `EntitlementChangeLog`: append-only history for entitlement snapshot changes.
- `dispatch_billing_outbox` management command and Celery task.
- `billing_sync_health` management command for monitoring output.

## Why this exists

Payment systems must handle provider retries, duplicate webhooks, network failures, and partial outages. v15 gives billing an operational safety layer without coupling product apps directly to Stripe/Paddle/Lemon Squeezy.

## Recommended production flow

1. Webhook updates local billing tables.
2. Billing writes an outbox event in the same transaction.
3. A worker dispatches outbox events to product apps, queues, or internal APIs.
4. Entitlement snapshots are recalculated and logged.
5. Reconciliation jobs update `ProviderSyncState`.
6. Operators replay failed webhooks from admin/API when needed.

## New endpoints

```text
GET/POST /api/v1/billing/outbox/
POST     /api/v1/billing/outbox/dispatch/
GET/POST /api/v1/billing/provider-sync-states/
GET      /api/v1/billing/webhooks/replays/
POST     /api/v1/billing/webhooks/replays/create/
GET      /api/v1/billing/entitlement-change-log/
POST     /api/v1/billing/entitlement-snapshots/recalculate-with-log/
```

## Scheduled jobs

Run outbox dispatch on a short interval:

```bash
python manage.py dispatch_billing_outbox --limit 100
```

Or schedule the Celery task:

```python
billing.tasks.dispatch_billing_outbox_task.delay(limit=100)
```

Monitor provider sync health:

```bash
python manage.py billing_sync_health
```

## Operational rules

- Never mutate entitlement snapshots without a reason.
- Prefer `recalculate-with-log` for admin/API recalculation.
- Webhook replay is staff-only and audit-visible.
- Outbox records are idempotency-keyed when possible.
- Provider sync lag should be alerted when it exceeds your SLA.

## Integration guidance

Product apps should consume entitlement snapshots or `/orgs/{slug}/entitlement-snapshot/`. Provider-specific objects should remain inside billing. This keeps blog, store, social, and other apps isolated from payment-provider outages and schema changes.
