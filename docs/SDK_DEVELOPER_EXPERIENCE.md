# SDK and Developer Experience

v30 introduces a production-oriented SDK and integration foundation for web, Android, Windows, CLI, and backend clients.

## Goals

- Give first-party apps a consistent auth integration surface.
- Keep web, Android, and Windows clients aligned with the same API contract.
- Track SDK releases and API compatibility inside the Django platform.
- Provide telemetry hooks for rollout monitoring without storing raw secrets.
- Make integration docs manageable through API-backed guide records.

## SDK packages

```text
sdks/typescript
sdks/android-kotlin
sdks/windows-dotnet
```

These are intentionally lightweight skeletons. They include login, refresh, profile, and organization entitlement helpers. Production apps should extend them with PKCE, secure token storage, retry/backoff, structured errors, and app-specific telemetry.

## Secure storage rules

### Web

Prefer first-party HttpOnly cookies for browser apps on the same parent domain. Avoid storing long-lived tokens in localStorage.

### Android

Use Android Keystore or EncryptedSharedPreferences for refresh-token material. Keep access tokens short-lived and preferably in memory.

### Windows

Use Windows Credential Manager, DPAPI, or an equivalent secure storage layer. Do not write refresh tokens to plain config files.

## SDK registry APIs

```text
GET      /api/v1/sdk/summary/
GET/POST /api/v1/sdk/releases/
POST     /api/v1/sdk/releases/{id}/publish/
POST     /api/v1/sdk/releases/{id}/deprecate/
GET/POST /api/v1/sdk/guides/
GET/POST /api/v1/sdk/compatibility/
GET/POST /api/v1/sdk/telemetry/
```

Public clients can read published release and guide metadata. Staff users can create releases, publish/deprecate versions, and manage compatibility rows.

## Release governance

Recommended release flow:

1. Create an SDK release record in draft state.
2. Upload package artifacts to your package registry or object storage.
3. Store the artifact URL and SHA-256 checksum.
4. Create compatibility rows for supported API versions.
5. Publish the release.
6. Monitor SDK telemetry events by platform and version.

## API compatibility

Use compatibility rows to avoid silent client breakage. Each SDK version should declare:

- API version support.
- Minimum server version.
- PKCE support.
- Refresh-token rotation support.
- Step-up auth support.
- Passkey support.

## Telemetry boundaries

SDK telemetry should not collect passwords, tokens, secrets, personal messages, payment card data, or raw device fingerprints. Use stable application IDs and coarse event types.

## Production checklist

- Publish SDK packages through a trusted registry.
- Sign release artifacts where possible.
- Enforce checksums for downloadable artifacts.
- Keep examples aligned with current endpoints.
- Add API contract tests for every supported SDK.
- Document token storage per platform.
- Maintain a deprecation policy for old SDK versions.
