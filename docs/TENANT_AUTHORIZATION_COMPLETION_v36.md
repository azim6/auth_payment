# v36 Tenant Authorization Completion

v36 completes the existing tenancy/RBAC foundation without introducing a new major feature area.

## Production goal

Every protected request should be authorized by:

```text
authenticated subject + organization tenant + permission code
```

not by a global user flag alone.

## Completed hardening

- Staff-only tenant authorization readiness report.
- Aggregate checks for organization owner coverage.
- Aggregate checks for active memberships.
- Invitation lifecycle readiness checks.
- Baseline role matrix coverage checks.
- Permission catalog and custom policy checks.
- Role grant readiness checks.
- Tenant service credential scope mapping checks.
- Audit coverage checks for organization and authorization operations.

## Endpoint

```http
GET /api/v1/tenancy/readiness/
```

This endpoint is staff-only and returns aggregate counts only. It does not expose invitation tokens, service credential hashes, user lists, or private tenant metadata.

## Required production authorization pattern

Application backends such as blog, store, and social should call the auth platform or use verified claims to answer questions like:

```text
Can user U perform permission P inside organization O?
```

Examples:

```text
blog.posts.create
store.orders.read
store.products.manage
social.posts.moderate
members.invite
billing.manage
```

## Access review checklist

Before production launch:

1. Confirm every organization has at least one active owner.
2. Confirm owner/admin/member/viewer baseline permissions match your business rules.
3. Confirm custom permission policies do not accidentally bypass billing or admin controls.
4. Confirm deny grants override custom allow grants where needed.
5. Confirm tenant service credentials are scoped to least privilege.
6. Confirm organization membership changes emit audit events.
7. Confirm invitation tokens are never logged or shown after creation.
8. Confirm web, Android, and Windows clients never send trusted `user_id` or `organization_id` values without server-side verification.

## What remains manual

v36 provides readiness checks and explicit authorization utilities. It does not automatically rewrite every app-specific endpoint. Blog, store, social, admin-console, and customer-portal views should still call permission helpers or endpoint-specific permission classes where business logic requires tenant authorization.
