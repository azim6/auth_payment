# Identity Hardening

Version 26 adds production-oriented identity assurance scaffolding for web, Android, Windows, and service/API clients.

## Goals

- Add passkey/WebAuthn-ready data structures without coupling the auth service to a single vendor.
- Track trusted devices for browser, Android, Windows, and API usage.
- Require fresh proof of identity before sensitive actions such as billing changes, MFA changes, API key creation, and admin actions.
- Maintain an append-only identity assurance event ledger for security investigations.
- Give administrators account recovery policy controls.

## New Django app

```text
identity_hardening/
├─ models.py
├─ serializers.py
├─ services.py
├─ views.py
├─ urls.py
├─ admin.py
└─ migrations/
```

## Main models

```text
PasskeyCredential
PasskeyChallenge
TrustedDevice
StepUpPolicy
StepUpSession
AccountRecoveryPolicy
IdentityAssuranceEvent
```

## API routes

```text
GET      /api/v1/identity/summary/

GET      /api/v1/identity/passkeys/
POST     /api/v1/identity/passkeys/register/begin/
POST     /api/v1/identity/passkeys/register/complete/
POST     /api/v1/identity/passkeys/authenticate/begin/
POST     /api/v1/identity/passkeys/{id}/revoke/

GET/POST /api/v1/identity/trusted-devices/
POST     /api/v1/identity/trusted-devices/{id}/revoke/

GET/POST /api/v1/identity/step-up-policies/       staff only
GET      /api/v1/identity/step-up-sessions/
POST     /api/v1/identity/step-up-sessions/satisfy/
POST     /api/v1/identity/step-up-sessions/check/
POST     /api/v1/identity/step-up-sessions/{id}/revoke/

GET/POST /api/v1/identity/recovery-policies/
GET      /api/v1/identity/assurance-events/
```

## Passkey/WebAuthn status

v26 is intentionally a **scaffold**, not a complete WebAuthn verifier. It stores challenges, credential metadata, public key material, counters, transports, attestation metadata, and audit events.

Before production passkey login is enabled, wire the registration and authentication completion endpoints to a vetted WebAuthn verifier. The verifier must check at least:

```text
challenge
origin
RP ID
client data hash
authenticator data
attestation statement, if required
assertion signature
credential ID
user presence
user verification
sign counter / clone detection
backup eligibility and state policy
```

Until that is implemented, keep passkeys behind a feature flag and continue requiring password + TOTP MFA for sensitive accounts.

## Step-up authentication

Step-up sessions are short-lived proof records used before sensitive actions. Example triggers:

```text
billing_change
password_change
mfa_change
api_key_create
admin_action
security_review
```

A staff user can define `StepUpPolicy` rows to decide what proof is required and how fresh it must be.

Example use case:

```text
1. User attempts to create an API key.
2. App checks /api/v1/identity/step-up-sessions/check/ with trigger=api_key_create.
3. If false, require passkey or TOTP verification.
4. App calls satisfy endpoint after verification.
5. API key creation proceeds only while the step-up session is valid.
```

## Trusted devices

`TrustedDevice` records are hashed server-side and should never store raw device IDs. Use this for:

```text
browser trusted device cookies
Android secure hardware-backed identifiers
Windows DPAPI/Windows Hello-backed identifiers
API client device binding
```

Treat trusted devices as risk signals, not absolute authorization.

## Account recovery policies

`AccountRecoveryPolicy` supports per-user and tenant-scoped recovery rules, including:

```text
allowed recovery methods
operator review requirements
MFA reset delays
cooldown periods
recovery contact email
```

Recovery operations should be logged to `IdentityAssuranceEvent` and, for high-risk accounts, connected to `security_ops` cases.

## Production checklist

- Add a real WebAuthn verifier before enabling passkey auth.
- Set RP ID and allowed origins per environment.
- Never store raw credential IDs, raw device IDs, or raw challenges after creation.
- Require step-up authentication for billing, MFA, password, admin, and API key changes.
- Send high-risk identity events into `security_ops` and `fraud_abuse`.
- Add feature flags before rolling out passkeys to all tenants.
