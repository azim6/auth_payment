# Release Notes v38

## Theme

Notifications and observability completion.

## Added

- Staff-only notification readiness endpoint.
- Staff-only observability readiness endpoint.
- Notification readiness checks for providers, templates, pending deliveries, failed deliveries, dead-letter deliveries, and queued events.
- Observability readiness checks for application events, metrics, traces, SLOs, SLO snapshots, alert rules, and open critical alerts.
- v38 tests for readiness report services.
- Completion documentation for notification and observability operations.

## New endpoints

```http
GET /api/v1/notifications/readiness/
GET /api/v1/observability/readiness/
```

## Notes

This release does not add a new major module. It improves operational confidence for modules already present in the platform.
