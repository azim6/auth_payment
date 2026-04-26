# Privacy and Compliance Workflows

v7 adds production foundations for privacy operations across web, Android, Windows, and service consumers.

## User-facing endpoints

```http
GET   /api/v1/privacy/preferences/
PATCH /api/v1/privacy/preferences/
GET   /api/v1/privacy/consents/
POST  /api/v1/privacy/consents/
GET   /api/v1/privacy/data-exports/
POST  /api/v1/privacy/data-exports/
GET   /api/v1/privacy/data-export-payload/
GET   /api/v1/privacy/account-deletion/
POST  /api/v1/privacy/account-deletion/
POST  /api/v1/privacy/account-deletion/confirm/
POST  /api/v1/privacy/account-deletion/cancel/
```

## Data export strategy

`GET /privacy/data-export-payload/` returns a synchronous JSON payload for small accounts and development. In production, `POST /privacy/data-exports/` should enqueue a Celery job that writes an encrypted archive to object storage and sets `download_url` on the request.

The scaffold intentionally keeps the object-storage implementation as a deployment decision because production choices vary between S3, Cloudflare R2, MinIO, Azure Blob, and local encrypted storage.

## Account deletion strategy

Deletion uses a safe staged process:

1. User requests deletion.
2. User confirms within the configured confirmation window.
3. Account is disabled immediately after confirmation.
4. Irreversible erasure/anonymization is deferred until the grace period expires.
5. Operators can review billing, fraud, tax, legal hold, and audit obligations before hard deletion.

Use `list_due_account_deletions` as the Celery/operator hook for the final erasure job.

## Consent model

`UserConsent` is append-only. Do not update historical consent rows. Record a new row whenever terms, privacy policy, analytics, or marketing consent changes.

## Recommended policy versioning

Use explicit version strings such as:

```text
terms-2026-04-24
privacy-2026-04-24
marketing-2026-04-24
analytics-2026-04-24
```

## Production notes

- Treat export URLs as sensitive secrets.
- Prefer short-lived signed URLs.
- Encrypt exported archives at rest.
- Log all data export and deletion events in `AuditLog`.
- Add legal-hold checks before physical deletion.
- Never hard-delete audit logs required for security investigations.
