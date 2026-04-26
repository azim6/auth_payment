# v5 OAuth/OIDC and Service Token Groundwork

Version 5 extends an authorization-code foundation so your central auth service can act as the login authority for separate web, Android, Windows, and service applications.

## Endpoints

```http
GET  /.well-known/openid-configuration
GET  /api/v1/oauth/authorize/
POST /api/v1/oauth/authorize/
POST /api/v1/oauth/token/
GET  /api/v1/oauth/jwks/
POST /api/v1/oauth/clients/      # admin only
GET  /api/v1/oauth/clients/      # admin only
```

## Supported flow

```text
1. Admin registers an OAuth client with exact redirect URIs.
2. App redirects the user to /oauth/authorize/ with response_type=code.
3. Auth service verifies the logged-in user and client request.
4. Auth service returns or redirects with a short-lived authorization code.
5. App exchanges that code at /oauth/token/.
6. Auth service returns access_token, refresh_token, and id_token.
```

## Confidential clients

Server-side apps should use `is_confidential=true` and store the one-time `client_secret` securely. The secret is hashed in the database and is only shown once when the client is created.

## Public clients

Mobile and desktop apps should use `is_confidential=false` and must use PKCE with `code_challenge` and `code_verifier`.

## Current v5 limits

v5 is intentionally a solid foundation, not a complete certified OIDC provider. Before opening it to third-party developers, add:

- consent screens
- RS256 or ES256 signing keys
- non-empty JWKS publishing
- per-client branding and privacy text
- user-facing connected-app management
- formal conformance testing

For first-party apps controlled by you, v5 is enough to begin integration testing of centralized login.

## v5 token lifecycle endpoints

v5 adds operational endpoints around the OAuth/OIDC foundation:

```http
GET  /api/v1/oauth/tokens/      # admin-visible issued token activity
POST /api/v1/oauth/introspect/  # validate whether a tracked token is active
POST /api/v1/oauth/revoke/      # revoke tracked token activity / blacklist refresh token
```

These endpoints are intentionally admin-only in v5. If you later want downstream services to call introspection directly, create a dedicated service credential with `tokens:introspect` and add a permission class that accepts service tokens.

## v5 service tokens

Trusted first-party services can use service credentials:

```http
POST /api/v1/service/token/
Content-Type: application/json

{
  "grant_type": "client_credentials",
  "service_key": "svc_...",
  "scope": "users:read"
}
```

The issued service token is short-lived and recorded in `OAuthTokenActivity` with token type `service`.


## v6 operational token controls

v6 adds refresh-token family records for first-party mobile and desktop clients. These records make logout-all, user security screens, and suspicious activity review easier. They do not remove the need to blacklist/rotate Simple JWT refresh tokens in production.
