import secrets
from urllib.parse import urljoin

from django.conf import settings
from django.utils import timezone

from .models import OAuthClaimMapping, OAuthScopeDefinition, OidcDiscoveryMetadataSnapshot, OidcSigningKey


def generate_key_id(prefix="kid"):
    return f"{prefix}_{secrets.token_urlsafe(24)}"


def publishable_jwks():
    keys = []
    for signing_key in OidcSigningKey.objects.filter(status__in=[OidcSigningKey.Status.ACTIVE, OidcSigningKey.Status.RETIRING]):
        jwk = dict(signing_key.public_jwk or {})
        jwk.setdefault("kid", signing_key.kid)
        jwk.setdefault("alg", signing_key.algorithm)
        jwk.setdefault("use", "sig")
        keys.append(jwk)
    return {"keys": keys}


def active_scope_names():
    return list(OAuthScopeDefinition.objects.filter(is_active=True).order_by("name").values_list("name", flat=True))


def active_claim_names():
    return list(
        OAuthClaimMapping.objects.filter(is_active=True, scope__is_active=True)
        .order_by("claim_name")
        .values_list("claim_name", flat=True)
        .distinct()
    )


def build_oidc_metadata(request=None):
    if request is not None:
        issuer = request.build_absolute_uri("/").rstrip("/")
    else:
        issuer = getattr(settings, "OIDC_ISSUER", "https://auth.example.com")
    return {
        "issuer": issuer,
        "authorization_endpoint": urljoin(f"{issuer}/", "api/v1/oauth/authorize/"),
        "token_endpoint": urljoin(f"{issuer}/", "api/v1/oauth/token/"),
        "jwks_uri": urljoin(f"{issuer}/", "api/v1/oidc/jwks/"),
        "userinfo_endpoint": urljoin(f"{issuer}/", "api/v1/oidc/userinfo/"),
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "refresh_token", "client_credentials"],
        "scopes_supported": active_scope_names() or ["openid", "profile", "email"],
        "claims_supported": active_claim_names() or ["sub", "email", "email_verified", "name"],
        "code_challenge_methods_supported": ["S256"],
        "id_token_signing_alg_values_supported": list(
            OidcSigningKey.objects.filter(status__in=[OidcSigningKey.Status.ACTIVE, OidcSigningKey.Status.RETIRING])
            .values_list("algorithm", flat=True)
            .distinct()
        ) or ["RS256"],
        "token_endpoint_auth_methods_supported": ["client_secret_basic", "client_secret_post", "none"],
        "revocation_endpoint": urljoin(f"{issuer}/", "api/v1/oauth/revoke/"),
        "introspection_endpoint": urljoin(f"{issuer}/", "api/v1/oauth/introspect/"),
        "generated_at": timezone.now().isoformat(),
    }


def create_metadata_snapshot(request, user=None):
    metadata = build_oidc_metadata(request)
    return OidcDiscoveryMetadataSnapshot.objects.create(
        issuer=metadata["issuer"],
        authorization_endpoint=metadata["authorization_endpoint"],
        token_endpoint=metadata["token_endpoint"],
        jwks_uri=metadata["jwks_uri"],
        userinfo_endpoint=metadata["userinfo_endpoint"],
        scopes_supported=metadata["scopes_supported"],
        claims_supported=metadata["claims_supported"],
        response_types_supported=metadata["response_types_supported"],
        grant_types_supported=metadata["grant_types_supported"],
        signing_alg_values_supported=metadata["id_token_signing_alg_values_supported"],
        metadata=metadata,
        generated_by=user if getattr(user, "is_authenticated", False) else None,
    )
