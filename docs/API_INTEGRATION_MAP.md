# v33 API Integration Map

## Web apps

Browser apps should use secure sessions where possible.

1. Redirect unauthenticated users to the auth service.
2. Store server-side sessions through Django session cookies.
3. Call `/api/v1/` auth endpoints for profile/session state.
4. Call `/api/v1/billing/orgs/{slug}/entitlements/` before enabling paid features.

## Android and Windows apps

Native clients should use short-lived access tokens and refresh-token rotation.

1. Login/register through auth API.
2. Store refresh tokens in platform secure storage.
3. Use `Authorization: Bearer <access_token>`.
4. Refresh before expiry.
5. Revoke token family on logout-all or suspected compromise.

## Blog/store/social services

Each service keeps its own product database and references central IDs.

- Blog: `author_user_id`, `comment_user_id`, `organization_id`.
- Store: `buyer_user_id`, `organization_id`, `subscription_entitlement_key`.
- Social: `actor_user_id`, `target_user_id`, `organization_id`.

Each service should call the auth/billing platform for:

- session/token validation,
- user profile summary,
- organization membership,
- permission checks,
- entitlement checks,
- audit/security event submission.

## Admin operations

Operators should use admin-console APIs for cross-module workflows and avoid direct database changes unless executing an approved incident runbook.

## Billing operations

Billing state should flow from provider webhooks into billing models, then into entitlements. Downstream apps should consume entitlements, not provider data.
