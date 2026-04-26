# v17 Compliance and Governance Operations

v17 adds a separate `compliance` app for governance workflows that sit across auth, billing, security operations, and tenant administration.

## What v17 adds

- Versioned policy documents for terms, privacy, DPA, acceptable-use, security, and billing policies.
- User and organization-scoped policy acceptance ledger.
- Two-person admin approval requests for high-risk operations.
- Audit export request metadata with checksums, record counts, expiry, and storage URI tracking.
- Evidence packs for security incidents, billing disputes, customer audits, and compliance reviews.
- Staff-only APIs and Django admin views for the governance objects.

## API surface

```text
GET/POST /api/v1/compliance/policies/
GET      /api/v1/compliance/policies/active/
GET/PATCH /api/v1/compliance/policies/{id}/
POST     /api/v1/compliance/policies/{id}/publish/

GET/POST /api/v1/compliance/policy-acceptances/

GET/POST /api/v1/compliance/approval-requests/
POST     /api/v1/compliance/approval-requests/{id}/review/

GET/POST /api/v1/compliance/audit-exports/
POST     /api/v1/compliance/audit-exports/{id}/mark-ready/

GET/POST /api/v1/compliance/evidence-packs/
GET/PATCH /api/v1/compliance/evidence-packs/{id}/
POST     /api/v1/compliance/evidence-packs/{id}/lock/
```

## Policy versioning

Policies are immutable by convention. Create a new `PolicyDocument` for every material update instead of editing an active policy in place.

Recommended versions:

```text
terms: 2026.04
privacy: 2026.04
dpa: 2026.04
security: 2026.04
billing: 2026.04
```

When a new active policy requires acceptance, apps should use:

```text
GET /api/v1/compliance/policies/active/
POST /api/v1/compliance/policy-acceptances/
```

## Two-person approval

Use `AdminApprovalRequest` before applying sensitive operations such as:

- custom billing override
- free/manual subscription grant
- security restriction
- user export
- account deletion
- policy publication
- webhook replay
- service-key rotation

The model intentionally rejects self-approval at the domain layer.

## Evidence packs

Evidence packs group relevant export records and context into one reviewable object. Examples:

- customer audit response
- billing dispute pack
- payment fraud investigation
- account takeover incident evidence
- quarterly compliance review

Use `evidence_index` for non-sensitive pointers only. Raw files should live in private storage with short-lived access controls.

## Security notes

- Do not expose audit export storage URIs publicly.
- Store audit export files in private object storage.
- Prefer compressed JSONL for audit/event exports.
- Include SHA-256 checksums for tamper-evidence.
- Use short retention for generated export files unless legally required otherwise.
- Require staff/admin permissions for all export and evidence-pack endpoints.

## Future work

Suggested v18 additions:

- Notification center for auth, billing, compliance, and security events.
- Customer-facing in-app notices for policy updates.
- Admin approval enforcement hooks inside billing/security operations.
- Background export generation jobs.
- WORM/object-lock storage integration.
