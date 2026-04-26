# v14 Billing Revenue Automation

v14 keeps payments separated from identity while making billing flexible enough for multi-project commercial operations.

## Added capabilities

- Admin-created discounts: percent, fixed amount, and free overrides.
- Customer-facing promotion codes mapped to discounts.
- Organization-specific promotion codes for private offers.
- Discount redemption ledger with idempotency keys.
- Billable add-ons for seats, quotas, one-time products, and metered preparation.
- Add-on entitlements that extend plan/subscription entitlements.
- Subscription add-ons attached to a subscription without changing the base plan.
- Entitlement snapshots so product apps can fetch a stable cached access payload.
- Manual entitlement recalculation after plan, discount, add-on, or subscription changes.

## Separation from auth

Auth still owns identity, sessions, MFA, organizations, membership, RBAC, OAuth/OIDC, service credentials, and audit logs.

Billing owns plans, prices, subscriptions, discounts, add-ons, invoices, payment provider records, and entitlement output.

Product apps should not query Stripe/Paddle directly. They should call the entitlement snapshot endpoint or the entitlement endpoint.

## Suggested commercial model

Use projects for products:

- `blog`
- `store`
- `social`
- `api`

Use plans for commercial bundles:

- `blog-free`
- `blog-pro`
- `store-starter`
- `store-growth`
- `platform-enterprise`

Use add-ons for optional expansion:

- `extra-seats-10`
- `extra-api-requests-100k`
- `custom-domain`
- `priority-support`
- `extra-store-products-1000`

Use entitlements as the contract consumed by product apps:

```json
{
  "store.enabled": true,
  "store.products.max": 5000,
  "blog.posts.max": 10000,
  "team_members.max": 25,
  "api.requests.monthly.max": 1000000
}
```

## Important security notes

- Promotions and manual discounts are staff-only by default.
- Redemptions are append-only and auditable.
- Use idempotency keys when redeeming discounts from checkout or admin flows.
- Do not treat promotion codes as authorization. They only affect billing price calculations.
- Always enforce feature access through entitlements and RBAC together.

## Operational workflow

1. Admin creates a project and plan.
2. Admin creates prices and base entitlements.
3. Admin creates discounts/promotion codes if needed.
4. Customer checks out through a provider session or receives a manual subscription.
5. Product apps read `/api/v1/billing/orgs/{slug}/entitlement-snapshot/`.
6. Staff recalculates snapshots when billing configuration changes.

## v14 endpoints

```text
GET/POST /api/v1/billing/discounts/
GET/POST /api/v1/billing/promotion-codes/
GET      /api/v1/billing/discount-redemptions/
POST     /api/v1/billing/discounts/redeem/
GET/POST /api/v1/billing/addons/
GET/POST /api/v1/billing/addon-entitlements/
GET      /api/v1/billing/subscription-addons/
POST     /api/v1/billing/subscription-addons/attach/
GET      /api/v1/billing/entitlement-snapshots/
POST     /api/v1/billing/entitlement-snapshots/recalculate/
GET      /api/v1/billing/orgs/{slug}/entitlement-snapshot/
```
