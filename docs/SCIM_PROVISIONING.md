# v28 SCIM Provisioning and Enterprise Directory Sync

v28 adds a dedicated `scim_provisioning` app for enterprise identity lifecycle automation. It is designed to work with the v27 enterprise SSO layer, organization tenancy, tenant-scoped RBAC, security operations, and compliance/audit features.

## Purpose

SCIM provisioning lets customers connect an external directory such as Okta, Microsoft Entra ID/Azure AD, Google Workspace, OneLogin, or a custom HRIS bridge. The auth platform can then maintain tenant users, groups, and deprovisioning state without manual admin work.

## Main objects

- `ScimApplication` - tenant-scoped SCIM integration with hashed bearer token storage.
- `DirectoryUser` - external directory user mapped to an optional local user.
- `DirectoryGroup` - external directory group mapped to tenant roles or permissions.
- `DirectoryGroupMember` - group membership edge for directory users.
- `DeprovisioningPolicy` - organization-level policy for disabled/deleted external users.
- `ScimSyncJob` - manual or scheduled sync/reconciliation run metadata.
- `ScimProvisioningEvent` - append-only lifecycle event log.

## Admin APIs

```http
GET/POST   /api/v1/scim/applications/
POST       /api/v1/scim/applications/{id}/activate/
POST       /api/v1/scim/applications/{id}/revoke/
POST       /api/v1/scim/applications/{id}/rotate-token/

GET/POST   /api/v1/scim/directory-users/
POST       /api/v1/scim/directory-users/{id}/deprovision/
GET/POST   /api/v1/scim/directory-groups/
GET/POST   /api/v1/scim/deprovisioning-policies/
GET/POST   /api/v1/scim/sync-jobs/
POST       /api/v1/scim/sync-jobs/{id}/start/
POST       /api/v1/scim/sync-jobs/{id}/complete/
GET        /api/v1/scim/events/
GET        /api/v1/scim/summary/
```

## Directory ingestion APIs

These endpoints are intentionally narrow and provider-neutral. They accept either `Authorization: Bearer scim_...` or `X-SCIM-Token: scim_...`.

```http
POST /api/v1/scim/v2/{application_id}/Users/upsert/
POST /api/v1/scim/v2/{application_id}/Users/deactivate/
POST /api/v1/scim/v2/{application_id}/Groups/upsert/
```

Example user upsert:

```json
{
  "external_id": "00u123",
  "user_name": "person@example.com",
  "email": "person@example.com",
  "display_name": "Person Example",
  "given_name": "Person",
  "family_name": "Example",
  "active": true,
  "attributes": {
    "department": "Engineering",
    "cost_center": "ENG"
  }
}
```

Example group sync:

```json
{
  "external_id": "group-admins",
  "display_name": "Admins",
  "mapped_role": "admin",
  "member_external_ids": ["00u123", "00u456"]
}
```

## Security notes

- SCIM tokens are displayed once and stored only as SHA-256 hashes.
- Rotate SCIM tokens regularly and immediately after vendor/admin changes.
- Keep SCIM tokens in a provider secret store, not in frontend code.
- Require HTTPS and strict host restrictions in production.
- Treat SCIM deprovisioning as high-impact; use grace periods or manual review for owners and billing owners.
- Wire group mappings into the v9 RBAC layer only after reviewing least-privilege defaults.
- For fully standards-compliant SCIM 2.0, add RFC-compatible `/Users`, `/Groups`, filtering, PATCH semantics, and schema discovery endpoints before advertising certification-level support.

## Production rollout checklist

```text
1. Verify the customer domain in enterprise_sso.
2. Create and activate a tenant SCIM application.
3. Copy the one-time SCIM token into the directory provider.
4. Configure user attribute mapping.
5. Configure group-to-role mappings.
6. Set the deprovisioning policy.
7. Run a dry-run sync job.
8. Review events and mismatches.
9. Enable live user and group provisioning.
10. Monitor SCIM events and security_ops risk events.
```
