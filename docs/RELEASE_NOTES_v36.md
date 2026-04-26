# Release Notes v36

## Theme

Tenant authorization completion and readiness hardening.

## Added

- `accounts.tenant_completion.build_tenant_authorization_readiness_report`.
- Staff-only `GET /api/v1/tenancy/readiness/` endpoint.
- Tenant authorization readiness audit event.
- Tenant/RBAC production completion documentation.
- v36 tenant authorization tests.

## Validation

- Changed Python files should AST-parse cleanly.
- Package zip should pass integrity testing.

## Upgrade guidance

Run the readiness endpoint in staging after creating seed organizations, memberships, permission policies, and tenant service credentials. Treat `fail` as a deploy blocker and `warn` as an access-review item.
