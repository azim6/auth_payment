# Release Notes v44

## Theme

Business-specific product rules for ZATCA, typing test, chat, and blog.

## Added

- New `business_rules` Django app enabled by default in the business profile.
- Product/action catalog for ZATCA, typing, chat, and blog.
- Access-check API for product apps.
- Access-summary API for customer/admin UI.
- Admin-created product access overrides.
- Usage event ledger for limited actions.
- Access decision audit records.
- Updated `seed_business_products` command to seed richer product-specific entitlements.
- New documentation: `docs/BUSINESS_RULES_v44.md`.

## New endpoints

```http
GET  /api/v1/business/catalog/
POST /api/v1/business/access-check/
POST /api/v1/business/access-summary/
GET/POST /api/v1/business/overrides/
POST /api/v1/business/overrides/{id}/deactivate/
GET  /api/v1/business/usage-events/
POST /api/v1/business/usage-events/reset/
GET  /api/v1/business/access-decisions/
```

## Business impact

ZATCA, typing, chat, and blog apps can now use one shared access engine for:

- subscription access
- free/manual access
- custom limits
- per-product blocking
- usage enforcement
- admin overrides

## Verification

- Zip integrity test passed.
- `__pycache__` files removed from package.
