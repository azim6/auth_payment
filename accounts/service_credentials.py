import secrets

from django.contrib.auth.hashers import check_password, make_password
from django.utils import timezone

from .models import ServiceCredential


ALLOWED_SERVICE_SCOPES = {
    "users:read",
    "users:write",
    "tokens:introspect",
    "tokens:revoke",
    "audit:read",
    "oauth:clients:read",
}


def generate_service_key() -> str:
    return f"svc_{secrets.token_urlsafe(40)}"


def service_key_prefix(raw_key: str) -> str:
    return raw_key[:16]


def hash_service_key(raw_key: str) -> str:
    return make_password(raw_key)


def verify_service_key(raw_key: str, encoded_hash: str) -> bool:
    return check_password(raw_key, encoded_hash)


def parse_scopes(scope_string: str) -> set[str]:
    return {scope for scope in scope_string.split() if scope}


def validate_service_scopes(scope_string: str) -> str:
    requested = parse_scopes(scope_string)
    unknown = requested - ALLOWED_SERVICE_SCOPES
    if unknown:
        raise ValueError(f"Unsupported service scopes: {', '.join(sorted(unknown))}")
    return " ".join(sorted(requested))


def find_valid_service_credential(raw_key: str) -> ServiceCredential | None:
    if not raw_key or not raw_key.startswith("svc_"):
        return None
    prefix = service_key_prefix(raw_key)
    credential = ServiceCredential.objects.filter(key_prefix=prefix, is_active=True).first()
    if not credential or credential.is_expired:
        return None
    if not verify_service_key(raw_key, credential.key_hash):
        return None
    credential.mark_used()
    return credential
