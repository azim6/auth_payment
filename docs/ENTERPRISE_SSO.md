# Enterprise SSO and SAML readiness

v27 adds an `enterprise_sso` app for enterprise identity-provider management while keeping the cryptographic SAML/OIDC assertion verifier intentionally pluggable.

## Core objects

- `EnterpriseIdentityProvider`: tenant-scoped SAML 2.0 or OIDC connection metadata.
- `VerifiedDomain`: DNS/manual domain proof used to route `user@company.com` to the right tenant.
- `SsoPolicy`: organization-level SSO enforcement and JIT provisioning policy.
- `JitProvisioningRule`: claim/group to tenant role mapping.
- `SsoLoginEvent`: append-only SSO test/login/provisioning event ledger.

## Operating model

1. Organization owner or staff creates an IdP connection.
2. Organization verifies one or more email domains.
3. Staff or owner configures SSO policy.
4. SSO routing can determine whether `alice@example.com` must use enterprise SSO.
5. Login/assertion completion should be implemented using a vetted SAML/OIDC library before production federation is enabled.

## Security requirements before production SAML login

- Verify signed assertions using a maintained SAML library.
- Validate audience, recipient, destination, issuer, subject confirmation, and assertion expiry.
- Prefer SP-initiated login and keep IdP-initiated login disabled unless a customer requires it.
- Rotate signing/encryption keys with a documented overlap window.
- Log every success, failure, block, and JIT provisioning event.
- Require admin approval for activating or changing production enterprise IdPs.

## Primary APIs

```text
GET/POST /api/v1/enterprise-sso/idps/
POST     /api/v1/enterprise-sso/idps/{id}/test/
POST     /api/v1/enterprise-sso/idps/{id}/activate/
POST     /api/v1/enterprise-sso/idps/{id}/disable/
GET      /api/v1/enterprise-sso/idps/{id}/saml-metadata/

GET/POST /api/v1/enterprise-sso/domains/
POST     /api/v1/enterprise-sso/domains/{id}/check/
POST     /api/v1/enterprise-sso/domains/{id}/mark_verified/

GET/POST /api/v1/enterprise-sso/policies/
GET/POST /api/v1/enterprise-sso/jit-rules/
GET      /api/v1/enterprise-sso/events/
POST     /api/v1/enterprise-sso/routing/
GET      /api/v1/enterprise-sso/summary/
```

## Version status

v27 is enterprise SSO-ready scaffolding. The data model, admin workflows, policy controls, routing, event logging, and metadata placeholders are included. Production SAML/OIDC assertion validation should be connected in a later version.
