package com.example.authplatform

import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody

class AuthPlatformClient(
    private val baseUrl: String,
    private val httpClient: OkHttpClient = OkHttpClient(),
) {
    private var accessToken: String? = null
    private val jsonMediaType = "application/json; charset=utf-8".toMediaType()

    fun setAccessToken(token: String?) {
        accessToken = token
    }

    fun loginJson(email: String, password: String, mfaCode: String? = null): String {
        val mfa = if (mfaCode != null) ",\"mfa_code\":\"$mfaCode\"" else ""
        val body = "{\"email\":\"$email\",\"password\":\"$password\"$mfa}"
        return postJson("/api/v1/login/", body)
    }

    fun meJson(): String = getJson("/api/v1/me/")

    fun organizationEntitlementsJson(slug: String): String =
        getJson("/api/v1/billing/orgs/$slug/entitlements/")

    fun getJson(path: String): String {
        val request = baseRequest(path).get().build()
        return execute(request)
    }

    fun postJson(path: String, json: String): String {
        val request = baseRequest(path)
            .post(json.toRequestBody(jsonMediaType))
            .build()
        return execute(request)
    }

    private fun baseRequest(path: String): Request.Builder {
        val builder = Request.Builder()
            .url(baseUrl.trimEnd('/') + path)
            .header("Accept", "application/json")
        accessToken?.let { builder.header("Authorization", "Bearer $it") }
        return builder
    }

    private fun execute(request: Request): String {
        httpClient.newCall(request).execute().use { response ->
            val body = response.body?.string().orEmpty()
            if (!response.isSuccessful) {
                throw AuthPlatformException(response.code, body)
            }
            return body
        }
    }
}

class AuthPlatformException(val statusCode: Int, responseBody: String) :
    RuntimeException("Auth Platform request failed with $statusCode: $responseBody")
