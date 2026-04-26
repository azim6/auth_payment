# Roadmap

## v1 - base auth service

Completed:

- Custom UUID user model
- Email-first login
- JWT auth for Android, Windows, desktop, and service clients
- Session auth for browser clients
- `/me` and public profile endpoints
- Docker Compose deployment baseline

## v2 - email verification and password reset

Completed:

- Hashed account action tokens
- Email verification issue/resend/confirm flow
- Password reset request/confirm flow
- Celery-backed email tasks
- Configurable frontend verification and reset URLs
- Admin visibility for account tokens

## v3 - MFA/TOTP and recovery codes

Completed:

- TOTP authenticator app enrollment
- MFA enforcement for JWT and session login
- Recovery codes stored as password hashes
- Recovery-code regeneration
- MFA disable flow requiring password plus second factor
- MFA status endpoint

## v4 - OAuth/OIDC provider foundation

Completed:

- OAuth client registration model
- Authorization code model
- Authorization endpoint scaffold
- Token exchange endpoint scaffold
- PKCE support for public Android/Windows clients
- Client-secret support for confidential web/server clients
- OIDC discovery endpoint
- JWKS placeholder endpoint

## v5 - audit logs and service clients

Completed:

- Append-only audit log model
- Admin/API audit log views
- Service-to-service credentials
- Short-lived service access token issuance
- OAuth token activity tracking
- Token introspection endpoint
- Token revocation endpoint
- Admin-visible OAuth client activity

## v6 target

- Asymmetric JWT signing with RS256/ES256
- Public JWKS with key rotation
- Token validation middleware for downstream Django apps
- Consent screen scaffolding
- Per-client branding and login policy

## v7 target

- Trusted devices
- Risk-based MFA hooks
- Login anomaly detection
- Account recovery hardening
- Session/device management UI APIs


## v6 - operational hardening

- Track web session devices.
- Track JWT refresh-token families for Android, Windows, and API clients.
- Add user-facing session/device revoke controls.
- Add logout-all style refresh-token family revocation.
- Add service credential rotation and deactivation endpoints.
- Keep audit log coverage for these high-risk actions.

## v7 - consent and OIDC completeness

- Consent screens for third-party clients.
- RS256/ES256 signing keys and public JWKS.
- Pairwise subject identifiers.
- Token exchange hardening and client policy management.


## v7 completed

- Privacy preference API
- Append-only consent ledger
- Data export request model and payload endpoint
- Account deletion request/confirm/cancel workflow
- Celery hooks for export expiry and due deletion review
- Admin visibility for privacy operations

## v8 candidates

- Signed/encrypted object-storage exports
- Legal-hold model
- Admin impersonation with full audit trails
- SCIM-style user provisioning for enterprise customers
- OIDC conformance hardening and asymmetric signing keys

## v8 completed

- Organization/workspace tenant model
- Organization memberships with owner/admin/member/viewer roles
- Invitation tokens for tenant onboarding
- Tenant-scoped service credentials
- Admin visibility for tenant objects
- Tenant API documentation

## v9 candidates

- Dedicated owner-transfer workflow
- Tenant domain verification
- Tenant-aware billing/quota model
- SCIM-style user provisioning
- SAML/OIDC enterprise federation


## v9 - tenant authorization and RBAC

- Tenant permission catalog
- Permission policies
- Role permission grants
- Access-check endpoint
- User permission summary endpoint
- Service-scope to permission mapping

## v10 completed

Billing/payment-processing foundation added as a separate `billing` app:

- project-specific plans
- free/manual subscriptions
- custom price support
- billing customers linked to organizations or users
- entitlements for cross-project feature control
- invoices and normalized payment transactions
- webhook event persistence for provider integrations

## Suggested v11

Stripe integration:

- hosted checkout session creation
- customer portal session creation
- signed Stripe webhook verification
- subscription/invoice/payment synchronization
- provider idempotency keys
- retry-safe webhook processing

## v11 completed

- Stripe provider integration scaffold.
- Tenant/RBAC-protected checkout session creation.
- Tenant/RBAC-protected customer portal session creation.
- Stripe webhook signature verification endpoint.
- Idempotent provider event log processing.
- Subscription, invoice, and payment synchronization from webhook events.

## v12 proposed

- Payment provider retry/replay operations.
- Dunning workflow and grace-period access rules.
- Coupon/promotion-code management.
- Usage metering and quota enforcement.
- Billing analytics and revenue reports.

## v12 - subscription operations and usage controls

- Subscription change-request workflow.
- Admin plan/quantity/cancellation/resume/trial/grace operations.
- Seat-limit tracking for tenant memberships.
- Usage metric catalog.
- Append-only usage records with idempotency support.
- Organization usage summary endpoint.

## Suggested v13

- Tax/VAT profile support.
- Coupons, discounts, promo codes, and credits.
- Dunning workflow and failed-payment email automation.
- Provider reconciliation management command.

## v13 - invoicing, tax, refunds, and dunning

Implemented:

- Billing profile model for invoice details and customer-level numbering.
- Customer tax IDs with provider sync fields.
- Credit notes with issued/admin workflow.
- Refund request governance workflow.
- Dunning case model for failed-payment operations.
- Staff-only APIs for profiles, tax IDs, credit notes, refunds, and dunning.
- Operational documentation in `docs/INVOICING_TAX_DUNNING.md`.

Suggested v14:

- Provider reconciliation exports.
- Statement generation.
- Revenue reports.
- Scheduled invoice/dunning jobs.
- Deeper Stripe/Paddle webhook mapping for credit notes and refunds.

## v14

- Discounts and promotion codes.
- Organization-specific private offers.
- Discount redemption ledger and idempotency.
- Billable add-ons and add-on entitlements.
- Subscription add-ons.
- Entitlement snapshots for fast product-app access checks.

## v15 candidate

- Fraud/risk signals for checkout and account abuse.
- IP/device velocity checks for billing operations.
- Webhook replay controls and provider reconciliation dashboard.
- Provider-side coupon/discount synchronization.

## v15 - Billing reliability operations

- Transactional billing outbox.
- Provider sync health and reconciliation state.
- Webhook replay workflow.
- Entitlement change history.
- Management commands and Celery dispatch hook.

## Suggested v16

- Fraud/risk controls: suspicious account/payment detection, velocity limits, payment-risk scoring, manual review queues, and abuse prevention signals shared with auth/RBAC.

## v16 - Security operations for auth and billing

Implemented:

- Dedicated `security_ops` Django app.
- Risk event ledger for auth, billing, OAuth, service credentials, admin actions, and platform monitoring.
- Score-based severity classification.
- Staff-only risk event create/list/action APIs.
- Account restrictions for login, API, billing, payment review, and organization admin locks.
- Staff-only restriction lift API.
- Security incident/case-management model.
- User security state endpoint that consolidates active restrictions, open risk events, and open incidents.
- Admin panels for risk events, restrictions, and incidents.
- Documentation in `docs/SECURITY_OPERATIONS.md`.

Suggested v17:

- Enforcement middleware/hooks so login, checkout, API token, and refund flows automatically check restrictions.
- Risk rule engine and async signal enrichment.
- Device/IP/geolocation enrichment.
- Security notification emails and staff review SLA queues.

## v17 - Compliance governance and evidence packs

- Added separate `compliance` Django app.
- Added versioned policy documents.
- Added user/org policy acceptance ledger.
- Added admin approval workflow for high-risk operations.
- Added audit export request tracking with checksums and record counts.
- Added evidence packs for security, billing, customer audits, and compliance reviews.

## Suggested v18

- Cross-product notification center.
- User/admin notification preferences.
- Webhook/email/in-app notification delivery queues.
- Policy update notices and acceptance reminders.
- Billing/security/compliance operational notifications.

## v18 - Operations/deployment maturity

Added:

```text
ops Django app
public liveness endpoint
public customer status endpoint
staff-only readiness endpoint
environment safety checks
service health checks
maintenance windows
backup snapshot metadata
restore-run workflow
status incidents
release/version records
ops_healthcheck management command
ops_create_release management command
operations deployment runbook
```

Future v19 candidates:

```text
notification channels for incidents and maintenance
Slack/email/webhook alert delivery
SLO/SLA target tracking
error-budget reporting
background job observability
queue lag tracking
```

## v19 - Developer platform integrations

- Dedicated `developer_platform` app.
- First-party web, Android, Windows, service, and CLI application registrations.
- SDK token policies for platform-specific token safety.
- Outbound webhook subscriptions and delivery records.
- Integration audit events.
- Organization-level integration summary endpoint.

## v20 candidates

- Signed webhook delivery worker.
- Developer dashboard UI.
- SDK examples and generated clients.
- App consent screen hardening.

## v20 - Notification infrastructure

- Dedicated notification service layer for auth, billing, security, compliance, ops, and product events.
- Provider-neutral email, SMS, push, in-app, and webhook channels.
- Tenant-specific templates, user preferences, push-token registry, delivery logs, retry state, and suppression lists.

## Candidate v21

- In-app notification inbox and notification center APIs.
- Real provider adapters for SES/SendGrid, Twilio, FCM/APNs/WNS.
- Notification analytics, provider failover, and campaign-safe broadcast controls.

## v21 - Observability and SLOs

- Dedicated `observability` app.
- Structured application event ledger.
- Metric snapshot records for dashboards and alerting.
- Request trace metadata for auth, billing, notification, and integration flows.
- SLO definitions, SLO snapshots, and error-budget fields.
- Alert rules and alert incident workflow.
- `observability_snapshot` management command.

## Candidate v22

- OpenTelemetry middleware and exporters.
- Prometheus metrics endpoint.
- Queue lag and Celery worker heartbeat monitoring.
- Dashboard-ready aggregation APIs.
- Alert delivery through the notification app.

## v22 completed: data governance

- Data category and data asset catalog
- PII/payment-data classification
- Retention policy records
- Legal holds
- Data subject request workflow
- Retention job dry-run/execution records
- Append-only anonymization metadata ledger
- Inventory snapshots for compliance evidence

## Suggested v23

- Feature flag and configuration management service
- Per-tenant rollout controls
- Kill switches for auth, billing, notifications, and webhooks
- Safe gradual release controls for Android/Windows/web clients

## v23 - Fraud and abuse controls

Added a dedicated fraud and abuse layer with device fingerprint records, IP reputation, velocity rules, abuse signals, abuse cases, payment-risk reviews, enforcement hooks, and a production guide.

Suggested v24 focus: customer support operations, impersonation/session assistance with approval gates, support macros, safe account recovery workflows, and support audit evidence.

## v24 - Admin Console and Operator Workflows

Completed:

- dedicated `admin_console` app
- dashboard widget registry
- saved admin views
- operator task queue
- two-step bulk action request workflow
- staff notes linked to users, organizations, and platform objects
- dashboard snapshot API
- user and organization admin overview endpoints

Recommended next version:

- v25 customer self-service portal APIs and UI-ready workflows
- v27 passkeys/WebAuthn
- v27 enterprise SSO/SAML

## v25 - Customer Self-Service Portal

v25 adds an API-first customer portal for web, Android, and Windows clients. It includes profile settings, organization overviews, billing summaries, customer-managed API keys, support requests, and customer-visible activity logs.

Suggested v27 focus: passkeys/WebAuthn and step-up authentication for sensitive portal and billing operations.

## v27 - Identity hardening

- Dedicated identity hardening app.
- Passkey/WebAuthn registration and authentication ceremony scaffolding.
- Trusted device inventory for web, Android, Windows, and API clients.
- Step-up authentication sessions and admin-managed step-up policies.
- Account recovery policy records.
- Identity assurance event ledger.

Suggested next versions:

- v27: Enterprise SSO/SAML foundations and domain verification.
- v28: SCIM provisioning and HRIS identity lifecycle sync.
- v29: Full OIDC hardening with JWKS rotation and client consent.


## v27 - Enterprise SSO readiness

- Tenant-scoped SAML/OIDC identity provider records.
- Verified domain workflow for SSO routing.
- SSO enforcement policy and JIT provisioning rules.
- SAML metadata placeholder endpoint and SSO login event ledger.

## v28 candidate

- SCIM provisioning, directory sync records, group mapping sync, and user lifecycle automation.

## v28 - SCIM provisioning

Completed:

- dedicated `scim_provisioning` app
- tenant-scoped SCIM applications with hashed bearer tokens
- directory users and groups
- group membership sync records
- deprovisioning policy controls
- sync job metadata
- append-only provisioning events
- provider-neutral SCIM ingestion endpoints

Suggested next versions:

- v29 full OIDC hardening with JWKS key rotation and client consent
- v30 SDKs for TypeScript, Android/Kotlin, Windows/.NET, and CLI
- v31 usage-based billing finalization and provider reconciliation

## v29 completed

OIDC provider hardening with JWKS key lifecycle, consent ledger, scope/claim catalogs, client trust profiles, and refresh-token policy controls.

## v30 - SDK and developer experience

- Added SDK registry app.
- Added TypeScript SDK skeleton.
- Added Android Kotlin SDK skeleton.
- Added Windows .NET SDK skeleton.
- Added SDK release and compatibility metadata APIs.
- Added SDK telemetry event endpoint.
- Added example app folders.

## v31 completed

- Usage-based billing foundation.
- Meters, meter prices, usage events, aggregation windows, rated usage lines, prepaid credits, and reconciliation runs.
- New `usage_billing` app and `/api/v1/usage-billing/` route prefix.

## v32 suggested

- Tax, multi-currency, regional pricing, and provider export for rated usage lines.

## v32 completed

- Dedicated `tax_pricing` app.
- Currency catalog and sales region records.
- FX rate snapshot metadata for future revenue reporting.
- Tax jurisdiction and tax-rate configuration.
- Tax exemption verification workflow.
- Regional price book for plans.
- Tax-inclusive and tax-exclusive price resolution records.
- Localized invoice settings.

Suggested next versions:

- v33 revenue analytics: MRR/ARR, churn, expansion/contraction, cohort and payment-failure reporting.
- v34 infrastructure automation: Terraform, backup automation, restore drills, blue/green deployment notes.
- v35 QA/security hardening: contract tests, migration tests, load tests, dependency scanning, penetration-test checklist.

## v33 completed

- Stopped adding new broad feature modules.
- Added completion-first upgrade policy.
- Added production MVP scope.
- Added feature readiness matrix.
- Added API integration map for web, Android, Windows, blog, store, and social services.
- Added repository structure validation script.
- Added module inventory script.
- Added version metadata and completion policy flags.

## v34 suggested

- Complete Stripe billing edge cases and reconciliation.
- Add end-to-end billing entitlement smoke tests.
- Finish subscription status transitions and dunning actions.
- Add production seed fixtures for plans, projects, and common entitlements.

## v36: Tenant authorization completion

- Completed aggregate tenant/RBAC readiness reporting.
- Added owner coverage, permission catalog, policy/grant, invitation lifecycle, tenant service credential, and audit coverage checks.
- Continued completion mode: no new feature area introduced.

## v37: Admin/customer portal completion

Completion-mode release for operator and customer self-service workflows. Adds admin-console and portal readiness reports plus support-request escalation into operator tasks. No new feature area is introduced.

## v38: Notifications and observability completion

- Added staff-only notification readiness report.
- Added staff-only observability readiness report.
- Added readiness checks for providers, templates, delivery backlog, dead-letter deliveries, telemetry freshness, SLOs, and critical alerts.
- Added completion documentation and readiness tests.

Next completion priorities:

- v39: data governance, compliance, and audit export completion.
- v40: fraud/security operations completion.
- v41: deployment, backup, restore, and release hardening.

## v39: Admin integration contract

Completion-mode release focused on making this backend a secure target for the separate Admin Control Platform. Adds service credentials, HMAC request signing, admin-origin request audit records, and a stable API contract for admin-control integration.

## v40: Production boot validation

Planned: dependency install validation, migration validation, Docker Compose boot smoke test, OpenAPI export, and production readiness checklist consolidation.

## v40 - Production boot validation

Completed deployment preflight, health/smoke scripts, Docker health checks, and admin-system readiness validation.
