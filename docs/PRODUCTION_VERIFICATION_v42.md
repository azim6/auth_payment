# v42 Production Verification

v42 adds a dedicated `production_verification` app so the Auth + Payment Platform can prove it is ready for deployment and for control by the separate Admin Control Platform.

## Verifies

- required production apps are installed
- experimental apps are visible as experimental before activation
- production-critical settings such as `DEBUG`, `ALLOWED_HOSTS`, `SECRET_KEY`, secure cookies, and admin-integration settings
- URL modules import successfully
- migration graph can load
- required management commands exist
- database and cache connectivity respond
- admin-control contract paths are inventoried

## API

```http
GET  /api/v1/production-verification/verify/
POST /api/v1/production-verification/verify/
GET  /api/v1/production-verification/snapshots/
GET  /api/v1/production-verification/feature-flags/
POST /api/v1/production-verification/feature-flags/sync/
```

All endpoints are staff-only.

## CLI

```bash
python manage.py production_verify
python manage.py production_verify --persist
python manage.py production_verify --fail-on-warn
```

## Admin Control Platform usage

The separate admin system should call this endpoint on startup and before dangerous admin actions:

```http
GET /api/v1/production-verification/verify/
```

If status is `fail`, block dangerous operator actions until the backend is fixed.
