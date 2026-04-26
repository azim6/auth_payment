# Authorization and RBAC - v9

Version 9 adds tenant-scoped authorization on top of the organization model introduced in v8.

## Concepts

- **Organization**: tenant/workspace boundary.
- **Membership role**: owner, admin, member, or viewer.
- **Permission code**: normalized action string such as `members.invite` or `audit.read`.
- **Permission policy**: tenant-specific permission object that can be enabled, disabled, expired, and audited.
- **Role permission grant**: allow/deny mapping between a role and a policy.
- **Service scope mapping**: tenant service credentials map machine scopes such as `members:write` to permission codes.

## Baseline role permissions

Baseline permissions are defined in `accounts.authorization.ROLE_BASELINE_PERMISSIONS`. Policies extend or override these defaults.

## Main endpoints

```http
GET  /api/v1/permissions/catalog/
GET  /api/v1/orgs/{slug}/permissions/me/
POST /api/v1/orgs/{slug}/permissions/check/
GET  /api/v1/orgs/{slug}/permissions/matrix/
GET  /api/v1/orgs/{slug}/permissions/policies/
POST /api/v1/orgs/{slug}/permissions/policies/
PATCH /api/v1/orgs/{slug}/permissions/policies/{policy_id}/
DELETE /api/v1/orgs/{slug}/permissions/policies/{policy_id}/
GET  /api/v1/orgs/{slug}/permissions/grants/
POST /api/v1/orgs/{slug}/permissions/grants/
```

`DELETE` on a permission policy performs a safe disable instead of hard deletion.

## Production notes

- Treat permission codes as API contracts. Do not rename them casually.
- Keep tenant policies small and explicit. Avoid wildcard permissions for v1 deployments.
- Log every policy/grant change through `AuditLog`.
- Use access-check endpoints for admin tools; enforce critical authorization server-side in each app/service.
- For service credentials, keep scopes narrow and rotate keys regularly.
