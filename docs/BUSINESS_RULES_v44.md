# v44 Business Rules + Product Access Engine

v44 turns the trimmed Auth + Payment Core into a business-specific access authority for the current products:

- ZATCA document generator
- Typing test
- Chat app
- Blog

The goal is simple: every product app can ask this backend whether a user or organization is allowed to perform an action before doing paid or limited work.

## Enabled app

`business_rules` is now part of the default business profile.

Base route:

```http
/api/v1/business/
```

## Product catalog

The built-in catalog defines products, actions, required entitlements, and usage periods.

```http
GET /api/v1/business/catalog/
```

Example ZATCA actions:

- `generate_document`
- `export_pdf`
- `export_xml`
- `generate_qr`
- `use_premium_template`
- `create_business_profile`

Example typing actions:

- `start_test`
- `complete_test`
- `generate_certificate`
- `create_custom_test`
- `view_analytics`

Example chat actions:

- `send_message`
- `upload_file`
- `create_room`
- `use_ai_assistant`

Example blog actions:

- `comment`
- `write_post`
- `upload_media`
- `manage_comments`
- `use_seo_tools`

## Access check API

Product apps should call this before performing a paid/limited action.

```http
POST /api/v1/business/access-check/
```

Example request:

```json
{
  "organization_slug": "acme",
  "product": "zatca",
  "action": "generate_document",
  "quantity": 1,
  "record_usage": true,
  "idempotency_key": "zatca-doc-123"
}
```

Example allowed response:

```json
{
  "allowed": true,
  "reason": "allowed",
  "product": "zatca",
  "action": "generate_document",
  "limit": 1000,
  "used": 34,
  "remaining": 966,
  "plan_codes": ["zatca-pro"],
  "required": "zatca.enabled",
  "limit_key": "zatca.documents_per_month",
  "usage_event_id": "..."
}
```

Example denied response:

```json
{
  "allowed": false,
  "reason": "limit_exceeded",
  "product": "zatca",
  "action": "generate_document",
  "limit": 5,
  "used": 5,
  "remaining": 0,
  "period_key": "2026-04"
}
```

## Product access summary

The admin-control platform and customer portal can use this to show effective access.

```http
POST /api/v1/business/access-summary/
```

## Admin overrides

Staff/admin users can grant, deny, or limit a specific product/action for a user or organization.

```http
GET/POST /api/v1/business/overrides/
POST     /api/v1/business/overrides/{id}/deactivate/
```

Examples:

- give a customer free ZATCA document generation for one month
- block only chat uploads for an abusive account
- increase `zatca.documents_per_month` for a custom-price customer
- allow blog writing for a manually approved author

## Usage tracking

Usage events are append-only by default.

```http
GET  /api/v1/business/usage-events/
POST /api/v1/business/usage-events/reset/
```

Use reset only from the admin-control platform for support or billing correction cases.

## Access decision audit

Every access check records a lightweight decision record for support/debugging.

```http
GET /api/v1/business/access-decisions/
```

## Seed data

Run:

```bash
python manage.py seed_business_products
```

This seeds products, plans, prices, and entitlements from the same catalog used by the access engine.

## Integration rule

Each product app should call the access API instead of implementing subscription logic locally.

Correct:

```text
ZATCA app -> /api/v1/business/access-check/ -> generate document if allowed
```

Wrong:

```text
ZATCA app -> Stripe directly -> guess feature access
```
