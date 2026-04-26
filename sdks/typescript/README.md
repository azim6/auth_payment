# Auth Platform TypeScript SDK

Production client skeleton for web and Node.js integrations.

```ts
import { AuthPlatformClient } from "@auth-platform/sdk";

const client = new AuthPlatformClient({ baseUrl: "https://auth.example.com" });
const tokens = await client.login("user@example.com", "password");
const me = await client.me();
```

Use browser HttpOnly cookies for first-party web where possible. Use bearer tokens for mobile, desktop, CLI, and server-side integrations.
