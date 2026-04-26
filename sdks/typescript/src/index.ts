export type TokenPair = {
  access: string;
  refresh?: string;
};

export type AuthPlatformClientOptions = {
  baseUrl: string;
  clientId?: string;
  fetchImpl?: typeof fetch;
  accessToken?: string;
};

export class AuthPlatformError extends Error {
  constructor(public status: number, message: string, public body?: unknown) {
    super(message);
  }
}

export class AuthPlatformClient {
  private readonly baseUrl: string;
  private readonly fetchImpl: typeof fetch;
  private accessToken?: string;

  constructor(options: AuthPlatformClientOptions) {
    this.baseUrl = options.baseUrl.replace(/\/$/, "");
    this.fetchImpl = options.fetchImpl ?? fetch;
    this.accessToken = options.accessToken;
  }

  setAccessToken(token: string | undefined): void {
    this.accessToken = token;
  }

  async login(email: string, password: string, mfaCode?: string): Promise<TokenPair> {
    const payload: Record<string, string> = { email, password };
    if (mfaCode) payload.mfa_code = mfaCode;
    const tokens = await this.request<TokenPair>("/api/v1/login/", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    this.accessToken = tokens.access;
    return tokens;
  }

  async refresh(refresh: string): Promise<TokenPair> {
    const tokens = await this.request<TokenPair>("/api/v1/token/refresh/", {
      method: "POST",
      body: JSON.stringify({ refresh }),
    });
    this.accessToken = tokens.access;
    return tokens;
  }

  async me<T = unknown>(): Promise<T> {
    return this.request<T>("/api/v1/me/");
  }

  async organizationEntitlements<T = unknown>(slug: string): Promise<T> {
    return this.request<T>(`/api/v1/billing/orgs/${encodeURIComponent(slug)}/entitlements/`);
  }

  async request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const headers = new Headers(init.headers);
    headers.set("Accept", "application/json");
    if (init.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
    if (this.accessToken) headers.set("Authorization", `Bearer ${this.accessToken}`);

    const response = await this.fetchImpl(`${this.baseUrl}${path}`, { ...init, headers });
    const contentType = response.headers.get("content-type") ?? "";
    const body = contentType.includes("application/json") ? await response.json() : await response.text();
    if (!response.ok) {
      throw new AuthPlatformError(response.status, `Auth Platform request failed with ${response.status}`, body);
    }
    return body as T;
  }
}
