# v40 Production Boot Validation

This release completes the first operational validation layer for the Auth + Payment Platform. It is designed to make the backend safe to connect to the separate Admin Control Platform.

## Goal

Before production rollout, operators should be able to answer:

- Can Django boot with production settings?
- Can the app reach PostgreSQL and Redis?
- Are secure cookies, CSRF, CORS, hosts, and secrets configured?
- Are Stripe/email/backups configured or intentionally deferred?
- Can the Admin Control Platform verify backend readiness without database access?

## New endpoint

```http
GET /api/v1/ops/production-validation/
```

Access: staff only.

The separate Admin Control Platform should call this endpoint together with:

```http
GET /api/v1/admin-integration/readiness/
GET /api/v1/billing/readiness/
GET /api/v1/auth/readiness/
GET /api/v1/tenancy/readiness/
```

## New command

```bash
python manage.py ops_production_preflight --json
```

Use this in CI/CD and before deployments. It exits non-zero when strict checks fail.

## New scripts

```bash
make production-bootstrap
make production-preflight
make smoke-http BASE_URL=https://auth.example.com
make docker-smoke
```

## Production launch checklist

1. Copy `.env.example` to `.env`.
2. Set a long random `SECRET_KEY`.
3. Set `DEBUG=false`.
4. Configure `ALLOWED_HOSTS`.
5. Configure `CSRF_TRUSTED_ORIGINS` and `CORS_ALLOWED_ORIGINS` for admin/frontend domains.
6. Configure PostgreSQL and Redis URLs.
7. Configure Stripe secrets before accepting payments.
8. Configure SMTP before enabling account lifecycle emails.
9. Configure backup storage before storing live customer data.
10. Run `make production-bootstrap`.
11. Run `make smoke-http BASE_URL=https://auth.example.com`.
12. Verify from the Admin Control Platform readiness screen.

## Admin-system compatibility

The Admin Control Platform should not connect directly to the auth/payment database. v40 provides readiness and validation APIs so the admin system can safely verify backend state through API calls only.
