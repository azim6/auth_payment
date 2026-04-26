# v13 invoicing, tax, refunds, and dunning

v13 adds operational billing governance around the existing auth + billing platform. It is intentionally provider-neutral so Stripe, Paddle, Lemon Squeezy, or manual billing can all feed the same internal records.

## New concepts

### Billing profile

`BillingProfile` stores structured invoice details for a `BillingCustomer`:

- legal name
- billing email and phone
- address fields
- country
- tax exemption status
- default currency
- invoice numbering prefix and sequence

Keep this separate from the auth profile. Auth identity data answers who the user is; billing profile data answers who receives invoices and tax documents.

### Customer tax IDs

`CustomerTaxId` stores VAT/GST/EIN-style registrations and provider sync IDs. Status values are:

- pending
- verified
- unverified
- rejected

The platform stores metadata and provider IDs, but card and bank details must remain inside the payment provider.

### Credit notes

`CreditNote` records adjustments against an invoice or customer balance. Use this for service credits, price adjustments, duplicate invoices, or customer-requested credits.

Credit notes are numbered through the customer billing profile sequence. This gives the admin team deterministic numbering for exports and reconciliation.

### Refund requests

`RefundRequest` separates refund governance from payment execution:

1. Staff creates a refund request.
2. Staff approves or rejects it.
3. Staff or a provider webhook marks it processed.
4. The linked payment transaction can be marked refunded.

This avoids allowing arbitrary immediate refunds from a normal app user flow.

### Dunning cases

`DunningCase` tracks failed billing attempts, grace periods, retry windows, restrictions, and resolution status. Your product apps should consume entitlements and subscription status, not provider payment state directly.

## New endpoints

```text
GET  /api/v1/billing/profiles/
POST /api/v1/billing/profiles/

GET  /api/v1/billing/tax-ids/
POST /api/v1/billing/tax-ids/

GET  /api/v1/billing/credit-notes/
POST /api/v1/billing/credit-notes/issue/

GET  /api/v1/billing/refunds/
POST /api/v1/billing/refunds/
POST /api/v1/billing/refunds/{id}/review/

GET  /api/v1/billing/dunning-cases/
POST /api/v1/billing/dunning-cases/
```

All v13 admin endpoints use staff-only access by default. Product-facing apps should continue using entitlement and usage endpoints.

## Security rules

- Never store card numbers, CVV, or raw bank account data.
- Keep refunds behind staff/admin access and audit logs.
- Treat tax IDs as sensitive business identifiers.
- Keep provider webhook idempotency enabled.
- Restrict product access through entitlements, not direct invoice/payment state.

## Provider sync

Provider integrations should map external events into internal durable records:

- `invoice.*` -> `Invoice`
- `payment_intent.*` / `charge.*` -> `PaymentTransaction`
- `credit_note.*` -> `CreditNote`
- `refund.*` -> `RefundRequest` / `PaymentTransaction`
- payment failures -> `DunningCase`

v13 adds the internal records and workflows. A later version should expand provider-specific sync depth and reconciliation exports.
