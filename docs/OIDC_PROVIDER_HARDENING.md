# OIDC Provider Hardening - v29

v29 turns the earlier OAuth/OIDC foundation into a stronger provider-control plane for first-party web, Android, Windows, service, and future partner clients.

## What v29 adds

- JWKS signing-key lifecycle metadata.
- Public JWKS endpoint that only exposes active/retiring keys.
- Scope catalog with sensitivity, consent, and staff-approval flags.
- Claim mapping catalog for ID token, UserInfo, and access-token claims.
- Client trust profiles for first-party, partner, third-party, and internal-service clients.
- Refresh-token rotation and reuse-detection policy records.
- Consent-grant ledger and consent evaluation endpoint.
- Token-exchange policy records for PKCE, nonce, redirect URI, and grant-type controls.
- OIDC discovery metadata snapshot records for compliance evidence.

## Production security notes

Do not store raw private signing keys in the database. Use `private_key_reference` to point to KMS, HSM, Vault, AWS KMS, GCP KMS, Azure Key Vault, or another secret-backed key service.

Recommended key rotation lifecycle:

1. Create a new key as `pending`.
2. Publish public JWK metadata.
3. Move it to `active`.
4. Mark the old key as `retiring` and keep it published until all issued tokens expire.
5. Move the old key to `retired`.
6. Use `revoked` only for compromise or emergency response.

## Consent model

First-party applications may be configured to skip a visible consent screen. Partner and third-party clients should require consent when scopes request personal, billing, organization, or administrative data.

The consent evaluation endpoint checks requested scopes, known scope definitions, client trust profile, active consent grants, and missing consent-required scopes.

## Endpoint summary

```text
GET      /api/v1/oidc/summary/
GET      /api/v1/oidc/.well-known/openid-configuration/
GET      /api/v1/oidc/jwks/
POST     /api/v1/oidc/consent/evaluate/

GET/POST /api/v1/oidc/signing-keys/
POST     /api/v1/oidc/signing-keys/{id}/activate/
POST     /api/v1/oidc/signing-keys/{id}/mark-retiring/
POST     /api/v1/oidc/signing-keys/{id}/retire/
POST     /api/v1/oidc/signing-keys/{id}/revoke/

GET/POST /api/v1/oidc/scopes/
GET/POST /api/v1/oidc/claims/
GET/POST /api/v1/oidc/trust-profiles/
POST     /api/v1/oidc/trust-profiles/{id}/review/
GET/POST /api/v1/oidc/refresh-token-policies/
GET/POST /api/v1/oidc/token-exchange-policies/
GET/POST /api/v1/oidc/consents/
POST     /api/v1/oidc/consents/{id}/revoke/
GET      /api/v1/oidc/metadata-snapshots/
POST     /api/v1/oidc/metadata-snapshots/create_snapshot/
```

## Next hardening work

- Connect ID token signing to a vetted JOSE/JWT library and key manager.
- Add full UserInfo endpoint claim rendering.
- Add signed metadata statements for partner clients.
- Add formal OIDC conformance test profiles.
- Add dynamic client registration only after approval workflows and abuse controls are complete.
