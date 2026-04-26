# v20 Notification Infrastructure

v20 adds a dedicated `notifications` Django app for production auth, billing, security, compliance, ops, and product communication. It is intentionally separate from `accounts` and `billing`, but it can consume `user_id`, `organization_id`, project codes, billing events, and security events.

## Goals

- One notification layer for web, Android, Windows, admin, billing, and security events.
- Separate user preferences from account identity.
- Store durable event and delivery records for auditability.
- Support provider-neutral email, SMS, push, in-app, and webhook channels.
- Keep provider secrets outside the database.
- Allow tenant-specific templates and global fallback templates.
- Support suppression lists for unsubscribes, bounces, complaints, and admin blocks.

## Core models

```text
NotificationProvider
NotificationTemplate
NotificationPreference
DevicePushToken
NotificationEvent
NotificationDelivery
NotificationSuppression
```

## API routes

```http
GET/POST /api/v1/notifications/providers/          staff only
GET/POST /api/v1/notifications/templates/
GET/POST /api/v1/notifications/preferences/
GET/PATCH/DELETE /api/v1/notifications/preferences/{id}/
GET/POST /api/v1/notifications/push-tokens/
POST /api/v1/notifications/push-tokens/{id}/revoke/
GET/POST /api/v1/notifications/events/
POST /api/v1/notifications/events/{id}/dispatch/
GET /api/v1/notifications/deliveries/
POST /api/v1/notifications/deliveries/{id}/dispatch/
GET/POST /api/v1/notifications/suppressions/      staff only
GET /api/v1/notifications/orgs/{slug}/summary/
```

## Security model

- Non-staff users can manage their own preferences and push tokens.
- Organization owners/admins can manage tenant templates and tenant notification events.
- Staff users can manage global providers and suppression lists.
- Device push tokens are hashed; only a token prefix is kept for admin visibility.
- Suppression records store recipient hashes, not plain email/phone values.
- Template variables must be validated by product code before dispatching sensitive events.

## Provider integration

`notifications.services.dispatch_delivery()` is a safe placeholder. It currently records local successful delivery unless `NOTIFICATION_DELIVERY_MODE=disabled`. Production providers should be implemented behind this adapter:

```text
email: Amazon SES, SendGrid, Mailgun, Postmark
sms: Twilio, MessageBird, AWS SNS
push: Firebase Cloud Messaging, APNs, Windows Push Notification Services
in-app: database-backed notification inbox
webhook: existing developer_platform webhook infrastructure
```

## Recommended event types

```text
auth.email_verification
auth.password_reset
security.mfa_enabled
security.risk_event_created
billing.checkout_started
billing.invoice_paid
billing.payment_failed
billing.subscription_canceled
compliance.policy_published
ops.incident_created
project.blog.comment_created
project.store.order_paid
project.social.mention_created
```

## Operational notes

- Run the Celery task `dispatch_due_notifications` on a short interval.
- Keep provider credentials in environment variables or a secrets manager.
- Use idempotency keys for provider webhook-triggered notifications.
- Treat marketing preferences separately from security/billing critical notifications.
- Never include raw payment details, password reset tokens, MFA secrets, or full API keys in notification payloads.
