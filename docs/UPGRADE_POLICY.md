# Upgrade Policy After v33

The project now follows a completion-first upgrade policy.

## Allowed upgrade work

- Finish incomplete implementation inside existing modules.
- Improve tests, migrations, permissions, and documentation.
- Add provider-specific adapters for billing, notifications, SSO, fraud, or tax where the abstraction already exists.
- Add frontend/API usability for existing admin and portal workflows.
- Add performance, reliability, security, and compliance hardening.

## Discouraged work

- Adding unrelated major modules.
- Adding vendor-specific code directly into product apps.
- Expanding admin functions without audit logs and permission checks.
- Enabling scaffolded enterprise features before verifier/provider libraries are integrated.

## Version direction

- v34-v35: Stripe/payment and subscription completion.
- v36-v37: Admin/customer portal workflow completion.
- v38-v39: Auth hardening, WebAuthn verifier, OIDC key rotation.
- v40-v41: Test suite, migrations, load/security validation.
