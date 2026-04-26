# v23 Fraud and Abuse Controls

The `fraud_abuse` app adds a provider-neutral fraud, abuse, and payment-risk layer. It is separate from core auth and billing, but it can promote severe signals into `security_ops` restrictions, risk events, and cases.

## Scope

v23 covers:

- device fingerprint records using hashed fingerprints only
- IP reputation records for internal or external reputation feeds
- append-only abuse signals
- velocity rules and velocity events
- abuse investigation cases
- payment-risk review queue
- safe enforcement hooks through `security_ops.AccountRestriction`
- subject risk summary APIs

## Design rule

Fraud controls must not directly store raw browser fingerprints, full card data, or payment credentials. Store stable hashes, normalized risk facts, provider IDs, and operational metadata.

## Typical flow

1. Auth, billing, notification, or platform code emits a velocity event.
2. Velocity rules evaluate recent activity for user, organization, IP, device, or global scope.
3. Matched rules create idempotent abuse signals.
4. Staff can promote an abuse signal to a security risk event and/or abuse case.
5. Staff can apply safe enforcement using account restrictions.

## Key endpoints

```text
GET/POST /api/v1/fraud-abuse/devices/
GET/PATCH /api/v1/fraud-abuse/devices/{id}/
GET/POST /api/v1/fraud-abuse/ip-reputation/
GET/PATCH /api/v1/fraud-abuse/ip-reputation/{id}/
GET/POST /api/v1/fraud-abuse/signals/
POST /api/v1/fraud-abuse/signals/{id}/promote/
GET/POST /api/v1/fraud-abuse/velocity-rules/
GET/PATCH /api/v1/fraud-abuse/velocity-rules/{id}/
GET /api/v1/fraud-abuse/velocity-events/
POST /api/v1/fraud-abuse/velocity-events/record/
GET/POST /api/v1/fraud-abuse/cases/
GET/PATCH /api/v1/fraud-abuse/cases/{id}/
POST /api/v1/fraud-abuse/cases/{id}/action/
GET/POST /api/v1/fraud-abuse/payment-risk-reviews/
POST /api/v1/fraud-abuse/payment-risk-reviews/{id}/action/
POST /api/v1/fraud-abuse/enforce/
POST /api/v1/fraud-abuse/summary/
```

## Recommended default rules

Start with monitor/review rules before using hard blocking:

```text
auth.login_failed per IP: 20 in 5 minutes -> review
auth.password_reset_requested per user: 5 in 1 hour -> challenge
billing.checkout_created per organization: 10 in 10 minutes -> review
billing.payment_failed per organization: 5 in 1 day -> payment_review
api.token_failed per IP: 50 in 5 minutes -> restrict
notifications.email_bounced per organization: 25 in 1 day -> review
```

## Enforcement modes

`FRAUD_ABUSE_ENFORCEMENT_MODE` is intentionally conservative:

```text
manual    staff reviews signals and applies restrictions manually
challenge future hook for MFA/CAPTCHA/payment verification challenge
restrict future hook for automatic short-lived restrictions
```

Do not enable automatic blocking until your false-positive rate is measured.

## Payment risk review

`PaymentRiskReview` links risk decisions to organizations, customers, subscriptions, invoices, transactions, and abuse signals. It is designed for cases such as:

- trial abuse
- high-risk custom price requests
- repeated payment failures
- disputed invoices
- suspicious checkout velocity
- mismatched organization/payment country signals

## Privacy and compliance

- Hash device fingerprints before storing them.
- Treat IP reputation as personal data in privacy jurisdictions that classify IP addresses as personal data.
- Use retention policies from `data_governance` for abuse signals and reputation feeds.
- Keep manual review notes factual and evidence-based.
