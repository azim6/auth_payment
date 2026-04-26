# Android Example

Wire `sdks/android-kotlin` into an Android app module and store refresh tokens with EncryptedSharedPreferences or a hardware-backed keystore.

Recommended flow:

1. Register Android application in `/api/v1/platform/applications/`.
2. Enable PKCE in the SDK token policy.
3. Use access tokens only in memory.
4. Rotate refresh tokens and revoke device sessions on logout.
