# Release Notes: v39 Admin Integration Contract

v39 completes the integration surface needed by a separate admin-control project.

## Added

- `admin_integration` Django app.
- Admin service credentials for the separate admin backend.
- HMAC request-signing helpers.
- DRF authentication class for signed admin-control calls.
- Admin-origin request audit middleware.
- Admin API scope catalogue.
- Admin API contract endpoint catalogue.
- Admin integration readiness endpoint.
- Credential rotation/deactivation APIs.
- Request-audit listing API.
- Signing verification endpoint for integration tests.
- v39 admin integration contract documentation.

## New endpoints

```http
GET  /api/v1/admin-integration/readiness/
GET  /api/v1/admin-integration/credentials/
POST /api/v1/admin-integration/credentials/
POST /api/v1/admin-integration/credentials/{id}/rotate/
POST /api/v1/admin-integration/credentials/{id}/deactivate/
GET  /api/v1/admin-integration/scopes/
GET  /api/v1/admin-integration/contract/
GET  /api/v1/admin-integration/request-audits/
POST /api/v1/admin-integration/verify-signed-request/
```

## Validation

- Python AST syntax parse passed for v39 changed files.
- Zip integrity test passed.
