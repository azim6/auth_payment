import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone as dt_timezone
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.utils import timezone
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken, UntypedToken

from .models import AuthorizationCode, OAuthClient, OAuthTokenActivity, ServiceCredential


def generate_client_id() -> str:
    return f"cli_{secrets.token_urlsafe(24)}"


def generate_client_secret() -> str:
    return f"sec_{secrets.token_urlsafe(40)}"


def hash_client_secret(secret: str) -> str:
    return make_password(secret)


def verify_client_secret(secret: str, encoded_hash: str) -> bool:
    if not encoded_hash:
        return False
    return check_password(secret, encoded_hash)


def generate_authorization_code() -> str:
    return f"code_{secrets.token_urlsafe(48)}"


def hash_authorization_code(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def create_authorization_code(*, client: OAuthClient, user, redirect_uri: str, scope: str, state: str = "", nonce: str = "", code_challenge: str = "", code_challenge_method: str = "") -> tuple[str, AuthorizationCode]:
    raw_code = generate_authorization_code()
    code = AuthorizationCode.objects.create(
        client=client,
        user=user,
        code_hash=hash_authorization_code(raw_code),
        redirect_uri=redirect_uri,
        scope=scope,
        state=state,
        nonce=nonce,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method,
        expires_at=timezone.now() + timedelta(minutes=settings.OIDC_AUTHORIZATION_CODE_LIFETIME_MINUTES),
    )
    return raw_code, code


def build_redirect_uri(base_uri: str, *, code: str, state: str = "") -> str:
    payload = {"code": code}
    if state:
        payload["state"] = state
    separator = "&" if "?" in base_uri else "?"
    return f"{base_uri}{separator}{urlencode(payload)}"


def find_valid_authorization_code(raw_code: str) -> AuthorizationCode | None:
    code_hash = hash_authorization_code(raw_code)
    return AuthorizationCode.objects.filter(code_hash=code_hash, used_at__isnull=True).select_related("client", "user").first()


def verify_pkce(*, verifier: str, challenge: str, method: str) -> bool:
    if not challenge:
        return True
    if not verifier:
        return False
    if method == "S256":
        digest = hashlib.sha256(verifier.encode("ascii")).digest()
        computed = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
        return hmac.compare_digest(computed, challenge)
    if method == "plain":
        return hmac.compare_digest(verifier, challenge)
    return False


def expires_from_payload(payload: dict) -> datetime:
    return datetime.fromtimestamp(int(payload["exp"]), tz=dt_timezone.utc)


def token_payload(raw_token: str) -> dict:
    token = UntypedToken(raw_token)
    return dict(token.payload)


def record_issued_token(*, raw_token: str, token_type: str, user=None, client: OAuthClient | None = None, service_credential: ServiceCredential | None = None, scope: str = "", metadata: dict | None = None) -> OAuthTokenActivity | None:
    try:
        payload = token_payload(raw_token)
    except TokenError:
        return None
    jti = payload.get("jti")
    exp = payload.get("exp")
    if not jti or not exp:
        return None
    record, _created = OAuthTokenActivity.objects.update_or_create(
        jti=jti,
        defaults={
            "token_type": token_type,
            "user": user,
            "client": client,
            "service_credential": service_credential,
            "scope": scope,
            "expires_at": expires_from_payload(payload),
            "metadata": metadata or {},
        },
    )
    return record


def issue_client_tokens(*, user, client: OAuthClient, scope: str, nonce: str = "") -> dict:
    refresh = RefreshToken.for_user(user)
    refresh["client_id"] = client.client_id
    refresh["scope"] = scope
    refresh["aud"] = client.client_id
    access = refresh.access_token
    access["client_id"] = client.client_id
    access["scope"] = scope
    access["aud"] = client.client_id

    id_token = RefreshToken.for_user(user).access_token
    id_token["token_use"] = "id"
    id_token["client_id"] = client.client_id
    id_token["aud"] = client.client_id
    id_token["email"] = user.email
    id_token["email_verified"] = user.email_verified
    id_token["preferred_username"] = user.username
    id_token["name"] = user.public_name
    if nonce:
        id_token["nonce"] = nonce

    raw_access = str(access)
    raw_refresh = str(refresh)
    raw_id = str(id_token)
    record_issued_token(raw_token=raw_access, token_type=OAuthTokenActivity.TokenType.ACCESS, user=user, client=client, scope=scope)
    record_issued_token(raw_token=raw_refresh, token_type=OAuthTokenActivity.TokenType.REFRESH, user=user, client=client, scope=scope)
    record_issued_token(raw_token=raw_id, token_type=OAuthTokenActivity.TokenType.ID, user=user, client=client, scope=scope)

    return {
        "access_token": raw_access,
        "refresh_token": raw_refresh,
        "id_token": raw_id,
        "token_type": "Bearer",
        "expires_in": int(settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds()),
        "scope": scope,
    }


def issue_service_access_token(*, credential: ServiceCredential) -> dict:
    access = AccessToken()
    access["token_use"] = "service"
    access["service_credential_id"] = str(credential.id)
    access["service_name"] = credential.name
    access["scope"] = credential.scopes
    raw_access = str(access)
    record_issued_token(
        raw_token=raw_access,
        token_type=OAuthTokenActivity.TokenType.SERVICE,
        service_credential=credential,
        scope=credential.scopes,
        metadata={"service_name": credential.name},
    )
    return {
        "access_token": raw_access,
        "token_type": "Bearer",
        "expires_in": int(settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds()),
        "scope": credential.scopes,
    }


def introspect_token(raw_token: str) -> dict:
    try:
        payload = token_payload(raw_token)
    except TokenError:
        return {"active": False}
    jti = payload.get("jti")
    if not jti:
        return {"active": False}
    record = OAuthTokenActivity.objects.filter(jti=jti).select_related("client", "user", "service_credential").first()
    if not record or not record.is_active:
        return {"active": False}
    record.mark_seen()
    result = {
        "active": True,
        "jti": jti,
        "token_type": record.token_type,
        "scope": record.scope,
        "exp": payload.get("exp"),
        "iat": payload.get("iat"),
        "client_id": record.client.client_id if record.client else "",
    }
    if record.user_id:
        result["sub"] = str(record.user_id)
    if record.service_credential_id:
        result["service_credential_id"] = str(record.service_credential_id)
        result["service_name"] = record.service_credential.name if record.service_credential else ""
    return result


def revoke_token(raw_token: str) -> bool:
    try:
        payload = token_payload(raw_token)
    except TokenError:
        return False
    jti = payload.get("jti")
    revoked_any = False
    if jti:
        record = OAuthTokenActivity.objects.filter(jti=jti).first()
        if record:
            record.revoke()
            revoked_any = True
    try:
        RefreshToken(raw_token).blacklist()
        revoked_any = True
    except Exception:
        pass
    return revoked_any
