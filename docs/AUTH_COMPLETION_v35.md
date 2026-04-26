# v35 Auth and Identity Completion

v35 continues the completion-mode direction started in v33. It does not add a new product area. It tightens and documents the existing authentication and identity stack so web, Android, Windows, API, and internal services have a clearer production readiness path.

## Completed areas

- Aggregate auth readiness report for staff/CI smoke checks.
- Readiness checks for custom user model, password hasher configuration, secure-cookie assumptions, account-token lifecycle, MFA, recovery codes, web session device inventory, refresh-token family inventory, OAuth clients, service credentials, audit logging, active account counts, and Django session counts.
- Staff-only audit event emitted when readiness is checked.
- Clear operator checklist for auth flows that must be exercised before production deploy.

## New endpoint

```text
GET /api/v1/auth/readiness/
```

Requires a staff/admin user. The response is aggregate-only and intentionally never returns raw session keys, access tokens, refresh tokens, MFA secrets, recovery codes, service keys, or user lists.

## Production auth acceptance checklist

Before launch, verify these flows against staging with HTTPS enabled:

1. Register a new web user.
2. Verify email.
3. Log in with a browser session.
4. Log in from Android/Windows using token auth.
5. Enable MFA and regenerate recovery codes.
6. Confirm MFA is required at login.
7. Reset password and verify old sessions/tokens are handled according to policy.
8. Revoke a browser session from device inventory.
9. Revoke all refresh-token families for a user.
10. Issue and rotate a service credential.
11. Confirm account/security audit events are written.
12. Confirm inactive users cannot authenticate.

## Known remaining hardening

- Connect passkey/WebAuthn completion endpoints to a vetted cryptographic verification library before enabling passkey login in production.
- Add integration tests that run the whole auth flow against a real PostgreSQL/Redis stack in CI.
- Decide whether password reset should revoke all active sessions by default for your risk model.
- Wire security_ops restrictions into every login/token/service-token path before accepting high-risk traffic.
- Add explicit device-bound refresh-token rotation if mobile/desktop clients require high-assurance sessions.
