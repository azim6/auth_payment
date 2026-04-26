# v8 Tenancy and Organizations

v8 adds an enterprise tenant layer on top of the central auth platform. The goal is to let the same identity service support individual users, teams, B2B customers, and first-party products such as blog, store, social, Android, Windows, and web clients.

## Core concepts

- `Organization`: tenant/workspace boundary.
- `OrganizationMembership`: user role inside a tenant.
- `OrganizationInvitation`: one-time token invitation for email-based onboarding.
- `TenantServiceCredential`: machine credential scoped to one organization.

## Roles

- `owner`: controls organization settings and can manage members.
- `admin`: can invite/manage members and tenant service credentials.
- `member`: normal authenticated organization user.
- `viewer`: read-only user.

Owner transfer is intentionally not implemented as a generic role update. Use a dedicated owner-transfer workflow in a future version so accidental ownership loss is impossible.

## API endpoints

```http
GET  /api/v1/orgs/
POST /api/v1/orgs/
GET  /api/v1/orgs/{slug}/
PATCH /api/v1/orgs/{slug}/
GET  /api/v1/orgs/{slug}/members/
PATCH /api/v1/orgs/{slug}/members/{membership_id}/
GET  /api/v1/orgs/{slug}/invitations/
POST /api/v1/orgs/{slug}/invitations/
POST /api/v1/orgs/invitations/accept/
GET  /api/v1/orgs/{slug}/service-credentials/
POST /api/v1/orgs/{slug}/service-credentials/
POST /api/v1/orgs/{slug}/service-credentials/{credential_id}/rotate/
POST /api/v1/orgs/{slug}/service-credentials/{credential_id}/deactivate/
```

## Tenant service credentials

Tenant service credentials start with `tsvc_` and are separate from platform-wide `svc_` service credentials. Use tenant credentials for integrations owned by a specific organization, for example a customer's ecommerce integration or automation worker.

Supported tenant scopes:

```text
org:read
org:write
members:read
members:write
users:read
audit:read
```

The raw key is returned only once. Store it in a secret manager. The database stores only the key prefix and password hash.

## Isolation policy

Application databases should continue to store product data separately and reference users by `user_id` and tenants by `organization_id`. Do not allow blog/store/social services to directly connect to the auth database. They should validate tokens and call tenant-aware APIs.

## Future hardening

- Dedicated owner-transfer flow.
- Tenant domain verification.
- SCIM provisioning.
- SAML/OIDC enterprise federation.
- Tenant-level audit export.
- Tenant-aware rate limits and billing quotas.
