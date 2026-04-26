# v18 Operations and Deployment Maturity

v18 adds an `ops` app for production operations around the auth, billing, security, and compliance platform.

## Goals

- Verify production environment safety before deployment.
- Expose staff-only readiness checks for deploy gates.
- Expose public liveness and public status endpoints.
- Track maintenance windows and customer-facing incidents.
- Track backup snapshots, restore rehearsals, and release metadata.
- Give staff a central operational control plane without mixing this logic into auth or billing.

## New endpoints

Public:

```http
GET /api/v1/ops/live/
GET /api/v1/ops/status/
```

Staff only:

```http
GET  /api/v1/ops/ready/
GET  /api/v1/ops/environment-checks/
POST /api/v1/ops/environment-checks/refresh/
GET  /api/v1/ops/health-checks/
POST /api/v1/ops/health-checks/refresh/

GET/POST   /api/v1/ops/maintenance-windows/
GET/PATCH  /api/v1/ops/maintenance-windows/{id}/

GET/POST   /api/v1/ops/backups/
GET/PATCH  /api/v1/ops/backups/{id}/
GET/POST   /api/v1/ops/restores/
POST       /api/v1/ops/restores/{id}/review/

GET/POST   /api/v1/ops/incidents/
GET/PATCH  /api/v1/ops/incidents/{id}/

GET/POST   /api/v1/ops/releases/
POST       /api/v1/ops/releases/{id}/deploy/
```

## Environment checks

The environment checker records whether the deployment has safe production defaults:

- `DEBUG` disabled
- non-default `SECRET_KEY`
- non-wildcard `ALLOWED_HOSTS`
- secure session cookie configuration
- configured CSRF trusted origins

Use the management command in CI/CD:

```bash
python manage.py ops_healthcheck
```

A non-ready deployment exits with a non-zero status.

## Health checks

The app checks core dependencies:

- database connectivity
- cache/Redis round-trip

The current design avoids leaking detailed diagnostics to anonymous users. Public `/live/` only says the app process is alive. Staff-only `/ready/` includes deeper operational state.

## Maintenance windows

Use maintenance windows to coordinate releases, migrations, and planned provider downtime.

Recommended workflow:

1. Create a scheduled maintenance window.
2. Announce the customer-facing message.
3. Switch it to active during the operation.
4. Mark it completed when verification passes.

## Backups and restores

`BackupSnapshot` stores metadata about backups. It does not directly run `pg_dump` or upload to storage because production backup execution is infrastructure-specific.

Recommended production implementation:

- run database snapshots from the infrastructure layer
- write `storage_uri`, `checksum_sha256`, `size_bytes`, and completion timestamps back to this model
- schedule restore rehearsals at least monthly
- never approve production restores without an evidence record and a second-person approval process

## Release records

Release records track deployed version, image tag, git SHA, changelog, and rollback notes.

Create release metadata in CI/CD:

```bash
python manage.py ops_create_release 18.0.0 --git-sha "$GIT_SHA" --image-tag "$IMAGE_TAG"
```

## Security rules

- Public health endpoints must never reveal secrets, stack traces, hostnames, DSNs, provider keys, or internal URIs.
- Backup and restore endpoints are staff-only and should be protected with MFA and admin approvals in production.
- Treat restore operations as sensitive compliance events.
- Track any production restore in compliance evidence packs.
