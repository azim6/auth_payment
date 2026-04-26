# Release Notes - v40

## Theme

Production boot validation and Admin Control Platform deployment compatibility.

## Added

- Staff-only production validation endpoint.
- Production preflight management command.
- Production bootstrap script.
- HTTP smoke-test script.
- Docker Compose Redis and web health checks.
- Environment variables for expected production hosts and admin origins.
- v40 tests for validation payload and endpoint shape.
- Documentation for deployment validation and admin-system compatibility.

## Changed

- Project version updated to `40.0.0`.
- OpenAPI metadata updated to `40.0.0`.
- `.env.example` updated with v40 validation controls.

## Production note

This release does not add new product scope. It makes existing auth, payment, and admin-integration systems easier to deploy, validate, and monitor before the separate Admin Control Platform connects to them.
