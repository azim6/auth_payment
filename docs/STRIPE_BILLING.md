# v11 Stripe Billing Integration

v11 keeps the billing app separated from the auth/RBAC system while adding a production-oriented Stripe integration layer.

## Responsibilities

Auth remains responsible for identity, MFA, sessions, tenant membership, RBAC, service credentials, and audit logs.

Billing is responsible for plans, prices, subscriptions, invoices, payments, checkout sessions, customer portal sessions, webhook processing, and entitlements.

## Checkout flow

1. Admin creates a `Project`, `Plan`, and `Price`.
2. The `Price.provider_price_id` is set to the Stripe price ID, for example `price_...`.
3. A tenant owner or billing admin calls:

```http
POST /api/v1/billing/checkout-sessions/create/
```

```json
{
  "organization_slug": "acme",
  "price_code": "store-pro-month",
  "success_url": "https://store.example.com/billing/success",
  "cancel_url": "https://store.example.com/billing/cancel"
}
```

4. The API verifies tenant billing access through RBAC.
5. The API creates or reuses the provider customer.
6. The API creates a Stripe Checkout Session and stores a local `CheckoutSession` record.
7. The frontend redirects the browser to `checkout_url`.
8. Stripe sends webhooks back to the auth/billing platform.
9. The billing app updates subscription, invoice, payment, and entitlement state.

## Customer portal flow

```http
POST /api/v1/billing/portal-sessions/create/
```

```json
{
  "organization_slug": "acme",
  "return_url": "https://store.example.com/billing"
}
```

Only tenant owners, staff, or users with `billing.manage` can create portal sessions.

## Webhook endpoint

```http
POST /api/v1/billing/webhooks/stripe/
```

The endpoint verifies Stripe's signature using `STRIPE_WEBHOOK_SECRET`. Invalid signatures are logged as failed webhook records and rejected.

Supported event families in v11:

- `checkout.session.completed`
- `customer.subscription.created`
- `customer.subscription.updated`
- `customer.subscription.deleted`
- `invoice.finalized`
- `invoice.paid`
- `invoice.payment_failed`
- `payment_intent.succeeded`
- `payment_intent.payment_failed`

## Environment variables

```env
BILLING_PROVIDER=stripe
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

Never commit provider secrets. Use deployment secrets or an encrypted secret manager.

## Security rules

- Never store card numbers.
- Never trust client-side price or plan data.
- Always load price and plan data from the server database.
- Always verify webhook signatures before processing provider events.
- Always make webhook processing idempotent.
- Always use tenant RBAC before creating checkout or portal sessions.
- Keep manual subscriptions/admin grants separate from provider-managed subscriptions.

## Provider abstraction

The Stripe implementation lives in `billing/payment_providers.py`. The rest of the billing app uses a small provider interface so future versions can add Paddle, Lemon Squeezy, or another provider without rewriting the plan/subscription/entitlement model.
