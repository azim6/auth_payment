# v22 Data Governance and Lifecycle Controls

v22 adds a dedicated `data_governance` app for production privacy, compliance, and operational data lifecycle controls across auth, billing, notifications, observability, and future first-party apps.

## Goals

- Maintain a catalog of data categories and assets.
- Classify PII, payment data, and restricted records.
- Define retention policies without hard-coding deletion rules into product apps.
- Track legal holds before automated deletion or anonymization.
- Govern data subject requests for access, export, deletion, correction, and restriction.
- Keep append-only anonymization records without storing raw PII.
- Generate data inventory snapshots for compliance evidence packs.

## Key concepts

### Data category

Examples:

```text
email-address
billing-tax-id
login-ip-address
notification-device-token
payment-provider-customer-id
```

Each category carries sensitivity, processing basis, PII/payment flags, and default retention guidance.

### Data asset

A governed table, API resource, external provider object, export location, or log stream.

Examples:

```text
accounts.User
billing.Invoice
notifications.PushDeviceToken
observability.TraceSample
stripe.customer
```

### Retention policy

A policy links assets/categories to a retention period and action:

```text
delete
anonymize
archive
review
```

v22 intentionally keeps the execution layer provider-neutral. Product apps should later register explicit retention handlers for destructive changes.

### Legal hold

Legal holds block automated retention execution for:

```text
specific users
specific organizations
specific data categories
global platform scope
```

This is essential for disputes, investigations, regulatory review, and billing chargebacks.

### Data subject request

Tracks governed privacy requests:

```text
access
export
delete
correct
restrict processing
object to processing
```

Requests have status, due dates, verification notes, scope metadata, and evidence checksums.

## Endpoints

```text
GET      /api/v1/data-governance/summary/
GET/POST /api/v1/data-governance/categories/
GET/PATCH /api/v1/data-governance/categories/{id}/
GET/POST /api/v1/data-governance/assets/
GET/PATCH /api/v1/data-governance/assets/{id}/
GET/POST /api/v1/data-governance/retention-policies/
GET/PATCH /api/v1/data-governance/retention-policies/{id}/
GET/POST /api/v1/data-governance/legal-holds/
POST     /api/v1/data-governance/legal-holds/{id}/release/
GET/POST /api/v1/data-governance/subject-requests/
POST     /api/v1/data-governance/subject-requests/{id}/action/
GET/POST /api/v1/data-governance/retention-jobs/
POST     /api/v1/data-governance/retention-jobs/plan/
POST     /api/v1/data-governance/retention-jobs/{id}/run/
GET      /api/v1/data-governance/anonymization-records/
GET      /api/v1/data-governance/inventory-snapshots/
POST     /api/v1/data-governance/inventory-snapshots/create/
```

All endpoints are staff-only in v22. Later versions can expose a limited self-service request endpoint for end users.

## Management command

```bash
python manage.py data_governance_snapshot
```

The command creates a point-in-time inventory snapshot and prints the summary.

## Production guidance

- Do not store raw PII in anonymization records; store hashes and metadata only.
- Destructive deletion/anonymization should require a per-app handler and a dry-run stage.
- Apply legal-hold checks before deletion, anonymization, or provider-side erasure.
- Link audit exports and evidence packs to inventory snapshots and subject-request IDs.
- Keep provider identifiers, not card data. Payment card data must remain inside the payment provider.
- Retention automation should run after backup windows and should emit audit/observability events.
