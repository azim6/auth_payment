# v33 Production MVP Scope

This is the recommended first production target for the platform.

## Must ship

- Registration, login, logout, email verification, password reset.
- MFA with recovery codes.
- JWT auth for Android, Windows, CLI, and API clients.
- Secure web sessions for browser apps.
- Organizations, invitations, memberships, tenant-scoped RBAC.
- Admin ability to suspend/limit users and organizations.
- Billing plans, custom prices, free/manual subscriptions, project-specific plans.
- Stripe checkout, customer portal, webhook ingestion, invoices, payment records.
- Entitlements for blog, store, social, API, and other services.
- Admin console APIs for user/org/billing/security overview.
- Customer portal APIs for profile, security, team, billing, and API keys.
- Health/readiness/status endpoints.
- Audit/security logs and basic notifications.

## Should not block first launch

- Enterprise SSO/SAML.
- SCIM provisioning.
- Public third-party OIDC provider certification.
- Multi-provider billing beyond Stripe.
- Advanced tax engine decisions.
- Full usage-based billing.
- Full SDK publishing program.

## Integration rule

All product apps should consume identity and billing state through APIs:

- `user_id` and `organization_id` come from auth/session/JWT validation.
- Permissions come from tenant-scoped RBAC.
- Product limits come from billing entitlements.
- Payment-provider records should not be queried directly by blog/store/social apps.
