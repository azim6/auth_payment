# Security Guide

## Core rules

- Only the auth service may connect to the auth database.
- All browser clients must use HTTPS in production.
- Use HttpOnly, Secure session cookies for browser authentication.
- Use JWT access + refresh tokens for Android, Windows, CLI, and other non-browser clients.
- Keep JWT access tokens short-lived.
- Rotate and blacklist refresh tokens.

## Account lifecycle security

- Email verification and password reset tokens are stored as SHA-256 hashes.
- Raw account action tokens are sent only once by email.
- Password reset responses do not reveal whether an email exists.
- Email verification resend responses do not reveal whether an email exists.
- Password reset tokens expire in 30 minutes.
- Email verification tokens expire in 24 hours.
- Issuing a new token marks existing unused tokens of the same purpose as used.

## Required production settings

Run this before deployment:

```bash
python manage.py check --deploy --settings=config.settings.production
```

Required environment values:

```text
DEBUG=false
SECRET_KEY=<long random value>
ALLOWED_HOSTS=auth.example.com
CSRF_TRUSTED_ORIGINS=https://auth.example.com
CORS_ALLOWED_ORIGINS=https://blog.example.com,https://store.example.com,https://social.example.com
DATABASE_URL=postgres://auth_user:password@db:5432/auth_db
REDIS_URL=redis://redis:6379/0
EMAIL_HOST=smtp.example.com
DEFAULT_FROM_EMAIL=no-reply@example.com
```

## Client guidance

### Browser apps

Prefer secure Django sessions with HttpOnly cookies when all apps live under the same root domain.

### Android and Windows apps

Use JWT access tokens in memory and store refresh tokens only in secure OS storage:

- Android: EncryptedSharedPreferences or Android Keystore-backed storage
- Windows: Windows Credential Manager or DPAPI-backed storage

## Operational guidance

- Back up PostgreSQL daily.
- Test restores monthly.
- Monitor error rates and auth failures.
- Use Sentry or equivalent error tracking.
- Rate-limit auth endpoints at reverse-proxy and application level.
- Configure SMTP reputation correctly: SPF, DKIM, DMARC.

## MFA/TOTP security notes added in v3

- TOTP secrets are signed with Django's signing framework before storage. In a hardened production deployment, replace this with envelope encryption through a KMS or Vault.
- TOTP verification allows a one-step clock drift window to tolerate normal client clock skew.
- Recovery codes are shown only once and stored with Django password hashing, not plaintext.
- Disabling MFA requires the current password plus a valid authenticator code or recovery code.
- JWT and browser session login both enforce MFA when a confirmed device exists.
- Regenerating recovery codes invalidates all previous unused recovery codes.

## OAuth/OIDC security notes added in v4

- OAuth clients require exact redirect URI matching.
- Confidential client secrets are stored as password hashes and shown only at creation time.
- Public Android/Windows clients should use PKCE with `S256`.
- Authorization codes are short-lived, single-use, and stored only as SHA-256 hashes.
- v4 publishes an empty JWKS because tokens are still signed with the configured SimpleJWT signing key. Do not expose symmetric signing keys. Add RS256/ES256 key rotation before third-party federation.
- Keep `OIDC_ISSUER` set to the public HTTPS origin of the auth service in production.

## v5 audit and service credential controls

### Audit logs

v5 adds `AuditLog` for authentication, OAuth, service credential, and admin/security actions. Treat this table as append-only operational evidence. Do not expose it to normal users. Restrict `/api/v1/audit/logs/` to staff/admin users only.

Recommended production practices:

- Forward audit logs to a central log system or SIEM.
- Alert on repeated failed token introspection or revocation operations.
- Alert when service credentials are created, used from a new IP, or used after long inactivity.
- Keep audit records according to your retention policy.

### Service credentials

Service credentials are intended for trusted first-party services only, such as blog, store, social, worker, and admin backend services.

Rules:

- Raw service keys are shown only once at creation.
- The database stores only a password hash and key prefix.
- Store raw service keys in a secret manager or encrypted VPS environment file.
- Scope credentials narrowly, for example `users:read` instead of broad write scopes.
- Set `expires_at` for every production service credential.
- Rotate keys periodically and immediately after suspected exposure.

### Token introspection and revocation

v5 records issued OAuth/client tokens and service tokens in `OAuthTokenActivity`.

- Use `/api/v1/oauth/introspect/` for high-risk downstream service checks.
- Use `/api/v1/oauth/revoke/` for administrative revocation.
- Refresh tokens are also passed to the Simple JWT blacklist flow.
- Access token revocation is tracked in `OAuthTokenActivity`; downstream services need introspection or centralized validation to observe it before token expiry.

### Next hardening step

v6 should replace symmetric OIDC signing with asymmetric RS256 or ES256 signing and publish public keys through JWKS with safe rotation.


## v6 device and token controls

v6 records web session devices and JWT refresh-token families. This is an operational visibility layer, not a replacement for Django sessions or Simple JWT blacklisting. Treat device records as security metadata and combine them with the audit log when investigating account compromise.

Service credentials now support rotation and deactivation. Rotation returns the new raw key once; store it in your secret manager immediately. Never log raw service keys.


## v7 privacy/security additions

- Data exports are modeled separately from synchronous payload generation so production systems can require encryption and signed URLs.
- Account deletion is staged, not immediate hard deletion, to avoid accidental destruction of records needed for fraud, billing, legal, or security review.
- Consent records are append-only. Do not mutate historical consent rows.
- Treat `download_url` as a secret. Use short expiry windows and server-side encryption.

## v10 billing security additions

- Billing is isolated in its own Django app and does not store card numbers.
- Apps should authorize feature access through entitlements, not payment provider state.
- Webhooks must be signature-verified before subscription changes are trusted.
- `BillingWebhookEvent` stores provider event IDs for idempotency and replay/debugging.
- Manual free/custom subscriptions are staff-only and should be reviewed through audit logs.
- Use provider-hosted checkout/customer portal pages for PCI scope reduction.

## v11 billing security notes

- Payment provider secrets must be injected through environment variables.
- Stripe webhook signatures must be verified before events are processed.
- Checkout session creation must use server-side `Price` records only.
- Tenant owners/staff/`billing.manage` users may create checkout and portal sessions.
- Apps should consume entitlements from the billing API and should not call payment providers directly.
- Webhook handlers are idempotent through `(provider, event_id)` uniqueness.

## v15 billing reliability security notes

- Treat webhook replay as a privileged staff operation.
- Store provider payloads only as needed for audit/replay, and avoid putting card data or raw secrets into webhook metadata.
- Outbox dispatchers should use service credentials with minimum required scope.
- Entitlement changes should always record a reason and actor when triggered by an admin.
- Provider sync health should be monitored; stale billing state can become an authorization and revenue-control risk.

## v17 governance controls

Use the `compliance` app for high-risk administrative workflows:

- Require two-person approval before custom billing overrides, sensitive account restrictions, user exports, account deletion, service-key rotation, and webhook replay.
- Keep generated audit exports in private storage only.
- Record SHA-256 checksums and record counts for every exported evidence file.
- Lock evidence packs once prepared so operational review can treat them as immutable.
- Never include full secrets, payment credentials, raw card data, or password hashes in an evidence pack.

## v18 operations security notes

- Public liveness and status endpoints must not expose secrets, database names, DSNs, provider keys, stack traces, or private network details.
- Staff readiness endpoints are intentionally protected by `IsAdminUser`.
- Backup and restore records are staff-only and should be handled as sensitive operational evidence.
- Production restore approval should use the v17 two-person admin approval workflow before any destructive restore is executed.
- Release records should include image tags and git SHAs so rollbacks are auditable.

## v21 observability security notes

Observability records must never include raw secrets, card data, password reset tokens, MFA recovery codes, full authorization headers, or unredacted payment-provider payloads. Use IDs, prefixes, hashes, trace IDs, and redacted metadata for correlation. Staff-only access is required for observability APIs because request traces and application events can reveal sensitive operational behavior.
