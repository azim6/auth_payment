# Release Notes v35

## Theme

Auth and identity completion.

## Summary

v35 keeps the project in completion mode and focuses on finishing the existing authentication layer rather than adding a new module. It adds a staff-only aggregate readiness report and documents the production acceptance path for web, Android, Windows, API, and service-to-service authentication.

## Added

- `accounts/auth_completion.py`
- `GET /api/v1/auth/readiness/`
- Staff audit event for readiness checks.
- Auth completion documentation.
- Auth readiness tests.

## Deployment notes

Run the endpoint in staging after migrations and seed data are loaded. A `warn` status can be acceptable when documented, but a `fail` status should block production release.
