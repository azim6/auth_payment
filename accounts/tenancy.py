import secrets

from django.contrib.auth.hashers import check_password, make_password
from django.utils import timezone

from .models import OrganizationInvitation, TenantServiceCredential


TENANT_SERVICE_SCOPES = {
    "org:read",
    "org:write",
    "members:read",
    "members:write",
    "users:read",
    "audit:read",
    "policies:read",
    "policies:write",
}


def generate_invitation_token() -> str:
    return f"invite_{secrets.token_urlsafe(36)}"


def hash_invitation_token(raw_token: str) -> str:
    return make_password(raw_token)


def invitation_token_matches(raw_token: str, encoded_hash: str) -> bool:
    return check_password(raw_token, encoded_hash)


def find_active_invitation(raw_token: str) -> OrganizationInvitation | None:
    if not raw_token or not raw_token.startswith("invite_"):
        return None
    # Invitation tokens are deliberately not prefix-indexed because invitation
    # acceptance is low-volume and should not expose lookup hints.
    for invitation in OrganizationInvitation.objects.filter(
        accepted_at__isnull=True,
        revoked_at__isnull=True,
        expires_at__gt=timezone.now(),
    ).select_related("organization")[:500]:
        if invitation_token_matches(raw_token, invitation.token_hash):
            return invitation
    return None


def generate_tenant_service_key() -> str:
    return f"tsvc_{secrets.token_urlsafe(40)}"


def tenant_service_key_prefix(raw_key: str) -> str:
    return raw_key[:16]


def hash_tenant_service_key(raw_key: str) -> str:
    return make_password(raw_key)


def validate_tenant_service_scopes(scope_string: str) -> str:
    requested = {scope for scope in scope_string.split() if scope}
    unknown = requested - TENANT_SERVICE_SCOPES
    if unknown:
        raise ValueError(f"Unsupported tenant service scopes: {', '.join(sorted(unknown))}")
    return " ".join(sorted(requested))


def find_valid_tenant_service_credential(raw_key: str) -> TenantServiceCredential | None:
    if not raw_key or not raw_key.startswith("tsvc_"):
        return None
    prefix = tenant_service_key_prefix(raw_key)
    credential = TenantServiceCredential.objects.select_related("organization").filter(
        key_prefix=prefix,
        is_active=True,
        organization__is_active=True,
    ).first()
    if not credential or credential.is_expired:
        return None
    if not check_password(raw_key, credential.key_hash):
        return None
    credential.mark_used()
    return credential
