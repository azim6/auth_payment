# v33 Feature Readiness Matrix

v33 changes the project direction from adding broad new modules to completing and hardening the modules already present. This file is the source-of-truth readiness map for future upgrades.

## Readiness levels

| Level | Meaning |
|---|---|
| L0 scaffold | Models/API skeleton exist, but production logic is incomplete. |
| L1 usable foundation | Core CRUD/API paths exist and are suitable for internal integration tests. |
| L2 production candidate | Has migrations, tests, permissions, docs, operational checks, and clear failure handling. |
| L3 hardened | Has provider integration, reconciliation, security review, load tests, and incident runbooks. |

## Production MVP modules

| Module | Current target | Required before launch |
|---|---:|---|
| accounts | L2 | Run full auth tests, verify JWT/session flows, finish WebAuthn before enabling passkeys. |
| billing | L2 | Complete Stripe webhook coverage, subscription reconciliation, invoice/payment edge-case tests. |
| security_ops | L1-L2 | Wire restrictions into auth and billing request paths. |
| ops | L2 | Validate health/readiness checks in Docker and VPS deployment. |
| admin_console | L1 | Build frontend or server-rendered operator screens on top of APIs. |
| customer_portal | L1 | Build profile/security/billing/team UI and test owner/member access boundaries. |
| notifications | L1-L2 | Connect real email/SMS/push providers and bounce/complaint processing. |
| observability | L1-L2 | Connect metrics/log shipping and define SLO alert policies. |

## Advanced modules to harden gradually

| Module | Current target | Recommended timing |
|---|---:|---|
| compliance | L1 | After first paying customers or audit requests. |
| data_governance | L1 | Before formal privacy/compliance obligations expand. |
| fraud_abuse | L1 | Before high-volume public signup or paid checkout campaigns. |
| identity_hardening | L1 | Enable passkeys only after vetted WebAuthn verification is integrated. |
| enterprise_sso | L0-L1 | Enable only for enterprise customers after SAML/OIDC verifier integration. |
| scim_provisioning | L0-L1 | Enable only after enterprise SSO customers need automated provisioning. |
| oidc_provider | L1 | Harden before third-party client access or public identity-provider promises. |
| sdk_registry | L1 | Useful once SDKs are published and versioned. |
| usage_billing | L1 | Enable after subscriptions require metered billing. |
| tax_pricing | L1 | Pair with Stripe Tax, Paddle, or a dedicated tax provider before relying on tax decisions. |
| developer_platform | L1 | Needed when internal or external apps consume platform APIs at scale. |

## v33 completion rule

Future versions should upgrade existing modules in this order:

1. Correctness and security fixes.
2. Provider integration completion.
3. Tests and migrations.
4. Operator/customer UX APIs.
5. Documentation and runbooks.
6. Performance and scale hardening.

Do not add new major modules unless an existing module cannot reasonably own the requirement.
