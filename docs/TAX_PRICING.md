# v32 Tax, Currency, and Regional Pricing

v32 adds a provider-neutral tax/pricing layer that keeps payment-provider objects separate from platform pricing policy.

## Goals

- Support multiple currencies and regional price books.
- Keep tax configuration auditable and separate from Stripe/Paddle provider state.
- Support tax-inclusive and tax-exclusive markets.
- Track tax exemptions and verification status.
- Provide a stable price-resolution API that billing, checkout, invoices, and customer portals can consume.

## Core models

- `Currency`: ISO-style currency metadata and minor units.
- `Region`: sales region/country grouping with default currency and tax-inclusive behavior.
- `ExchangeRateSnapshot`: manual/provider FX snapshots used for reporting and future price conversion.
- `TaxJurisdiction`: tax country/region configuration.
- `TaxRate`: time-bounded tax rate records.
- `TaxExemption`: verified buyer/user/organization exemptions.
- `RegionalPrice`: plan-specific regional price book.
- `LocalizedInvoiceSetting`: invoice language, prefixes, and tax labels per region.
- `PriceResolutionRecord`: immutable-ish quote/price calculation trace.

## API

All v32 endpoints are under `/api/v1/tax-pricing/`.

Important endpoints:

```text
GET/POST /api/v1/tax-pricing/currencies/
GET/POST /api/v1/tax-pricing/regions/
GET/POST /api/v1/tax-pricing/fx-rates/
GET/POST /api/v1/tax-pricing/tax-jurisdictions/
GET/POST /api/v1/tax-pricing/tax-rates/
GET/POST /api/v1/tax-pricing/tax-exemptions/
POST     /api/v1/tax-pricing/tax-exemptions/{id}/verify/
GET/POST /api/v1/tax-pricing/regional-prices/
GET/POST /api/v1/tax-pricing/invoice-settings/
POST     /api/v1/tax-pricing/resolve-price/
GET      /api/v1/tax-pricing/summary/
```

## Production notes

- Do not treat v32 as a full tax engine. Use provider APIs or a dedicated tax provider for final tax liability decisions.
- Keep `PriceResolutionRecord` for quote/audit traceability.
- Restrict tax exemption verification to trained staff and require evidence retention rules.
- For real-time checkout, pass resolved regional price/tax details into the billing provider session metadata.
- For multi-currency subscriptions, do not silently switch currencies mid-subscription without explicit user/admin action.

## Future upgrades

- Tax provider integration such as Stripe Tax, TaxJar, or Avalara.
- Automated FX rate imports.
- Region-specific checkout eligibility.
- Multi-currency revenue reporting.
- Localized invoice templates.
