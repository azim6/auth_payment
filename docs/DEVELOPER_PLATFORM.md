# v19 Developer Platform Integrations

v19 adds a dedicated `developer_platform` Django app for connecting the central auth/billing system to your first-party web, Android, Windows, service, and CLI projects.

## Goals

- Register project applications per organization and billing project.
- Keep client IDs stable while rotating secrets safely.
- Support public clients such as Android/Windows with PKCE and optional device binding policies.
- Support confidential clients such as server-rendered web apps and service backends with hashed client secrets.
- Let each first-party app subscribe to auth, billing, security, compliance, and ops events through outbound webhooks.
- Keep an integration audit trail for app registration, secret rotation, and webhook changes.

## Main models

| Model | Purpose |
|---|---|
| `DeveloperApplication` | App registration for web, Android, Windows, service, and CLI clients. |
| `SDKTokenPolicy` | Per-platform token constraints such as TTL, PKCE, attestation, and device binding. |
| `WebhookSubscription` | Outbound webhook endpoint for first-party project integrations. |
| `WebhookDelivery` | Durable delivery log for pending, delivered, failed, and dead-lettered webhook events. |
| `IntegrationAuditEvent` | Audit log for developer platform configuration changes. |

## Security rules

Only organization owners/admins or staff users can manage developer platform objects.

Client and webhook secrets are stored as password hashes. The raw value is returned once at creation or rotation time. Store it in a secret manager and never log it.

Use these client patterns:

- Web/server apps: confidential client with client secret.
- Android/Windows apps: public client with PKCE, short-lived tokens, and optional device binding.
- Service-to-service calls: prefer the existing service credential system for internal server calls; use `DeveloperApplication` only when the app needs OAuth/OIDC-style identity.

## Key endpoints

```text
GET/POST /api/v1/platform/applications/
GET/PATCH /api/v1/platform/applications/{application_id}/
POST /api/v1/platform/applications/{application_id}/rotate-secret/

GET/POST /api/v1/platform/sdk-token-policies/

GET/POST /api/v1/platform/webhooks/subscriptions/
GET/PATCH /api/v1/platform/webhooks/subscriptions/{subscription_id}/
POST /api/v1/platform/webhooks/subscriptions/{subscription_id}/rotate-secret/
GET /api/v1/platform/webhooks/deliveries/

GET /api/v1/platform/audit-events/
GET /api/v1/platform/orgs/{org_slug}/summary/
```

## Recommended event names

Use stable dotted event names:

```text
user.created
user.email_verified
user.mfa_enabled
organization.created
organization.member_added
billing.subscription.created
billing.subscription.changed
billing.invoice.paid
billing.payment.failed
security.risk_event.created
compliance.policy.published
ops.incident.created
ops.incident.resolved
```

## v20 candidates

- Signed webhook delivery worker with HMAC headers.
- App-level OAuth consent screens.
- Developer dashboard UI.
- SDK examples for Django, Next.js, Android/Kotlin, and Windows/.NET.
- Terraform/Docker deployment examples for multi-app tenants.
