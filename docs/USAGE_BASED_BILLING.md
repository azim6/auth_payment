# Usage-Based Billing

Version 31 adds a dedicated `usage_billing` app for metered billing across all first-party products.

## Goals

- Track raw usage events with idempotency keys.
- Aggregate usage into subscription billing windows.
- Rate usage into invoice-ready lines.
- Support free allowances, prepaid/manual credits, and provider reconciliation.
- Keep metered billing separate from identity while still linking to organizations, subscriptions, and entitlements.

## Main concepts

| Object | Purpose |
|---|---|
| `Meter` | Defines a billable metric such as `api.calls`, `storage.gb_hours`, or `emails.sent`. |
| `MeterPrice` | Defines how a meter is priced for a plan or add-on. |
| `UsageEvent` | Append-only raw usage event with an idempotency key. |
| `UsageAggregationWindow` | Aggregated quantity for a meter during a billing period. |
| `RatedUsageLine` | Invoice-ready usage charge after free allowance and credits. |
| `CreditGrant` | Prepaid/manual credit balance for an organization. |
| `CreditApplication` | Ledger entry for credit consumed by a rated usage line. |
| `UsageReconciliationRun` | Operational record for comparing local usage with provider/provider-invoice state. |

## Production notes

Usage ingestion must be idempotent. The uniqueness rule is:

```text
organization + meter + idempotency_key
```

Provider adapters should push `RatedUsageLine` records to Stripe/Paddle/Lemon Squeezy only after windows are finalized.

Do not let product apps write invoices directly. Product apps should only ingest usage events. Billing staff or scheduled jobs should aggregate, rate, and reconcile.

## API surface

```text
POST /api/v1/usage-billing/events/ingest/
GET  /api/v1/usage-billing/events/
POST /api/v1/usage-billing/windows/plan/
POST /api/v1/usage-billing/windows/{id}/finalize/
POST /api/v1/usage-billing/rated-lines/rate/
GET  /api/v1/usage-billing/orgs/{slug}/summary/
POST /api/v1/usage-billing/reconciliations/run/
```

## Recommended v32 work

- Tax/multi-currency/regional pricing.
- Provider adapters that export rated usage lines to Stripe billing meters or invoice items.
- Revenue recognition reports for usage lines and credits.
