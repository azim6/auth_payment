# Release Notes: v34

## Theme

Payment and subscription completion for the existing billing module.

## Highlights

- Hardened Stripe webhook idempotency path.
- Added entitlement recalculation after subscription, invoice, payment, checkout, and refund events.
- Added billing outbox emission for processed provider events.
- Added provider-side subscription operations for supported admin actions.
- Added Stripe refund creation from approved refund requests.
- Added staff-only billing readiness API.
- Added v34 payment completion tests and runbook.

## Upgrade notes

No database migration is required for v34. The release uses existing billing tables introduced in v10-v15.

## Recommended validation

```bash
make validate-structure
python manage.py test billing.tests.test_v34_payment_completion
```
