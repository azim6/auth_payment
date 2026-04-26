# v34 Payment Completion Notes

v34 changes the project direction from adding new billing features to finishing the existing payment subsystem.

## Completed in this release

- Stripe webhook processing now updates entitlement snapshots after provider events.
- Stripe webhook processing now emits billing outbox events for downstream apps.
- Checkout expiration is handled, not only checkout completion.
- Subscription webhook sync now carries `trial_end`, quantity, seat limit, period boundaries, and cancellation flags.
- Invoice payment failures now open or update dunning cases.
- Stripe refund processing is wired through the existing refund review workflow.
- Admin subscription changes can sync supported operations to Stripe:
  - quantity changes
  - cancel at period end
  - cancel immediately
  - resume
- A staff-only readiness endpoint summarizes missing Stripe settings, provider price coverage, failed webhooks, and provider sync state.

## New readiness endpoint

```http
GET /api/v1/billing/readiness/
```

This endpoint is staff-only and should be part of your deployment checklist.

## Production checklist

1. Configure `STRIPE_SECRET_KEY` and `STRIPE_WEBHOOK_SECRET`.
2. Make sure every active paid `Price` has a `provider_price_id`.
3. Create a Stripe CLI test checkout and replay the webhook to `/api/v1/billing/webhooks/stripe/`.
4. Confirm a `Subscription` row is created or updated.
5. Confirm an `EntitlementSnapshot` row is recalculated.
6. Confirm a `billing.provider_event.processed` outbox event is created.
7. Test `invoice.payment_failed` and confirm a `DunningCase` is opened.
8. Test cancellation and resume from the admin subscription-change workflow.

## Still intentionally not added

- No new major apps.
- No new payment provider.
- No tax expansion.
- No additional enterprise identity scope.

Next completion releases should continue closing gaps in already-added modules.
