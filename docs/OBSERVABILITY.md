# v21 Observability

v21 adds a dedicated `observability` app for production monitoring of the auth, billing, notification, developer-platform, security, compliance, and operations layers.

## Goals

- Store structured application events for high-value business/security flows.
- Capture metric snapshots that can feed dashboards and alerting.
- Track request trace metadata without storing secrets or request bodies.
- Define SLOs for critical journeys such as login, checkout, webhook processing, and token validation.
- Create alert rules and staff-managed alert incidents.

## Data model

```text
ApplicationEvent
MetricSnapshot
TraceSample
ServiceLevelObjective
SLOSnapshot
AlertRule
AlertIncident
```

## Security rules

- Do not store passwords, tokens, card data, provider secrets, authorization headers, or raw webhook payloads containing sensitive data in observability records.
- Use `request_id`, `trace_id`, `subject_type`, and `subject_id` for correlation.
- Keep payloads minimal and redacted.
- Observability APIs are staff-only by default.
- Long-term metrics should be exported to Prometheus, OpenTelemetry, Datadog, Grafana Cloud, or another dedicated telemetry platform.

## Endpoints

```text
GET      /api/v1/observability/summary/
GET/POST /api/v1/observability/events/
GET/POST /api/v1/observability/metrics/
GET/POST /api/v1/observability/traces/
GET/POST /api/v1/observability/slos/
GET/PATCH /api/v1/observability/slos/{id}/
POST     /api/v1/observability/slos/{id}/calculate/
GET      /api/v1/observability/slo-snapshots/
GET/POST /api/v1/observability/alert-rules/
POST     /api/v1/observability/alert-rules/{id}/evaluate/
GET      /api/v1/observability/alert-incidents/
POST     /api/v1/observability/alert-incidents/{id}/action/
```

## Management command

```bash
python manage.py observability_snapshot
```

The command records an observability heartbeat, calculates active SLO snapshots, and evaluates active alert rules.

## Recommended SLOs

```text
auth.login.success_rate
jwt.token.issue_success_rate
oauth.token_exchange_success_rate
billing.checkout_success_rate
billing.webhook_processing_success_rate
notifications.delivery_success_rate
api.p95_latency_ms
```

## Production integration path

v21 stores operational records inside Django for control-plane visibility. For high-volume systems, forward the same events and metrics to a telemetry backend and keep this Django app as an internal control-plane index.
