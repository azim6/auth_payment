# v16 Security Operations

v16 adds a dedicated `security_ops` app that connects secure auth and payment processing without mixing core auth or billing responsibilities.

## Purpose

The app centralizes operational security controls for:

- suspicious login and session activity
- suspicious checkout, payment, refund, dunning, or subscription activity
- OAuth/client and service-credential abuse signals
- staff-created account restrictions
- incident/case management for auth and billing investigations

## Core models

### SecurityRiskEvent

Append-only risk signal from auth, billing, OAuth, service credentials, admin actions, or platform monitoring.

Important fields:

- `category`: `auth`, `billing`, `oauth`, `service`, `admin`, or `platform`
- `signal`: machine-readable code such as `auth.impossible_travel` or `billing.refund_velocity`
- `score`: 0-100 normalized risk score
- `severity`: auto-classified from score
- `status`: `open`, `acknowledged`, `resolved`, or `false_positive`
- optional links to user, organization, and subscription

### AccountRestriction

Manual or automated control that limits a user or organization.

Supported restriction types:

- `login_block`
- `api_block`
- `billing_block`
- `payment_review`
- `org_admin_lock`

Restrictions can be temporary through `expires_at` or permanent until staff lift them.

### SecurityIncident

Case-management object for coordinated investigation and response. It can link multiple risk events and track containment/resolution notes.

## API endpoints

All endpoints are staff-only.

```text
GET/POST /api/v1/security/risk-events/
POST     /api/v1/security/risk-events/{id}/action/

GET/POST /api/v1/security/restrictions/
POST     /api/v1/security/restrictions/{id}/lift/

GET/POST /api/v1/security/incidents/
GET/PATCH /api/v1/security/incidents/{id}/

POST     /api/v1/security/users/state/
```

## How product apps should use it

Product apps should not read payment-provider fraud scores directly. Instead:

1. Billing/webhook/service code records risk signals.
2. Security ops aggregates risk events and restrictions.
3. Auth, billing, and product apps check active restrictions before sensitive operations.

Example sensitive operations:

- login
- password reset
- new API token/service credential
- checkout session creation
- refund approval
- plan downgrade/upgrade
- organization member invitation

## Recommended signals

```text
auth.failed_login_velocity
auth.impossible_travel
auth.mfa_recovery_code_velocity
auth.service_key_unusual_ip
billing.checkout_velocity
billing.payment_failed_velocity
billing.refund_velocity
billing.promotion_code_abuse
billing.webhook_signature_failure
oauth.suspicious_client_redirect
platform.admin_high_risk_action
```

## v17 candidates

- Middleware hooks to enforce restrictions automatically.
- Async risk rule engine.
- Geo/IP/device fingerprint enrichment.
- Staff review queues with SLA timers.
- Security notification emails.
