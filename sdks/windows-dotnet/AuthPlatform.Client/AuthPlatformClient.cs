using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;

namespace AuthPlatform.Client;

public sealed class AuthPlatformClient
{
    private readonly HttpClient _httpClient;
    private readonly string _baseUrl;
    private string? _accessToken;

    public AuthPlatformClient(string baseUrl, HttpClient? httpClient = null)
    {
        _baseUrl = baseUrl.TrimEnd('/');
        _httpClient = httpClient ?? new HttpClient();
    }

    public void SetAccessToken(string? token) => _accessToken = token;

    public Task<string> LoginAsync(string email, string password, string? mfaCode = null, CancellationToken cancellationToken = default)
    {
        var payload = new Dictionary<string, string>
        {
            ["email"] = email,
            ["password"] = password,
        };
        if (!string.IsNullOrWhiteSpace(mfaCode)) payload["mfa_code"] = mfaCode;
        return PostJsonAsync("/api/v1/login/", payload, cancellationToken);
    }

    public Task<string> MeAsync(CancellationToken cancellationToken = default) =>
        GetJsonAsync("/api/v1/me/", cancellationToken);

    public Task<string> OrganizationEntitlementsAsync(string slug, CancellationToken cancellationToken = default) =>
        GetJsonAsync($"/api/v1/billing/orgs/{Uri.EscapeDataString(slug)}/entitlements/", cancellationToken);

    public async Task<string> GetJsonAsync(string path, CancellationToken cancellationToken = default)
    {
        using var request = BuildRequest(HttpMethod.Get, path);
        using var response = await _httpClient.SendAsync(request, cancellationToken).ConfigureAwait(false);
        return await ReadOrThrowAsync(response, cancellationToken).ConfigureAwait(false);
    }

    public async Task<string> PostJsonAsync<T>(string path, T payload, CancellationToken cancellationToken = default)
    {
        using var request = BuildRequest(HttpMethod.Post, path);
        var json = JsonSerializer.Serialize(payload);
        request.Content = new StringContent(json, Encoding.UTF8, "application/json");
        using var response = await _httpClient.SendAsync(request, cancellationToken).ConfigureAwait(false);
        return await ReadOrThrowAsync(response, cancellationToken).ConfigureAwait(false);
    }

    private HttpRequestMessage BuildRequest(HttpMethod method, string path)
    {
        var request = new HttpRequestMessage(method, _baseUrl + path);
        request.Headers.Accept.Add(new MediaTypeWithQualityHeaderValue("application/json"));
        if (!string.IsNullOrWhiteSpace(_accessToken))
        {
            request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", _accessToken);
        }
        return request;
    }

    private static async Task<string> ReadOrThrowAsync(HttpResponseMessage response, CancellationToken cancellationToken)
    {
        var body = await response.Content.ReadAsStringAsync(cancellationToken).ConfigureAwait(false);
        if (!response.IsSuccessStatusCode)
        {
            throw new AuthPlatformException((int)response.StatusCode, body);
        }
        return body;
    }
}

public sealed class AuthPlatformException : Exception
{
    public int StatusCode { get; }
    public string ResponseBody { get; }

    public AuthPlatformException(int statusCode, string responseBody)
        : base($"Auth Platform request failed with {statusCode}")
    {
        StatusCode = statusCode;
        ResponseBody = responseBody;
    }
}
