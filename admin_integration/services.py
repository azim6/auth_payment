import hashlib
import hmac
import ipaddress
import secrets
import time
from dataclasses import dataclass

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.utils import timezone

from .models import AdminApiContractEndpoint, AdminApiScope, AdminIntegrationReadinessSnapshot, AdminRequestAudit, AdminServiceCredential

DEFAULT_ADMIN_SCOPES = {
    "admin:readiness": "Read readiness/status endpoints",
    "admin:read": "Read admin-console aggregate data",
    "admin:users:write": "Perform user/account administrative actions",
    "admin:billing:write": "Perform billing/subscription administrative actions",
    "admin:security:write": "Apply or lift security restrictions",
    "admin:entitlements:write": "Recalculate or override entitlements",
    "admin:ops:write": "Manage maintenance/ops objects",
    "admin:audit:read": "Read audit/compliance evidence data",
}

DEFAULT_ADMIN_CONTRACT = [
    ("auth", "GET", "/api/v1/auth/readiness/", "admin:readiness", "Auth stack readiness report"),
    ("tenancy", "GET", "/api/v1/tenancy/readiness/", "admin:readiness", "Tenant/RBAC readiness report"),
    ("billing", "GET", "/api/v1/billing/readiness/", "admin:readiness", "Billing/payment readiness report"),
    ("admin_console", "GET", "/api/v1/admin-console/readiness/", "admin:readiness", "Admin-console readiness report"),
    ("portal", "GET", "/api/v1/portal/readiness/", "admin:readiness", "Customer portal readiness report"),
    ("notifications", "GET", "/api/v1/notifications/readiness/", "admin:readiness", "Notification delivery readiness report"),
    ("observability", "GET", "/api/v1/observability/readiness/", "admin:readiness", "Observability readiness report"),
    ("ops", "GET", "/api/v1/ops/ready/", "admin:readiness", "Runtime readiness endpoint"),
    ("admin_console", "GET", "/api/v1/admin-console/users/{user_id}/overview/", "admin:read", "User control overview"),
    ("admin_console", "GET", "/api/v1/admin-console/orgs/{slug}/overview/", "admin:read", "Organization control overview"),
    ("security", "POST", "/api/v1/security/restrictions/", "admin:security:write", "Restrict a user or organization"),
    ("billing", "POST", "/api/v1/billing/entitlement-snapshots/recalculate-with-log/", "admin:entitlements:write", "Recalculate entitlement snapshot"),
]

def generate_admin_api_key():
    return f"adm_{secrets.token_urlsafe(42)}"

def generate_signing_secret():
    return f"ask_{secrets.token_urlsafe(48)}"

def body_sha256(body):
    return hashlib.sha256(body or b"").hexdigest()

def canonical_request(method, path, timestamp, nonce, body_hash):
    return "\n".join([method.upper(), path, timestamp, nonce, body_hash])

def sign_request(secret, method, path, timestamp, nonce, body_hash):
    payload = canonical_request(method, path, timestamp, nonce, body_hash).encode("utf-8")
    return hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()

def ip_allowed(ip, allowed_ranges):
    if not allowed_ranges:
        return True
    if not ip:
        return False
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    for item in allowed_ranges:
        try:
            if "/" in item and addr in ipaddress.ip_network(item, strict=False):
                return True
            if addr == ipaddress.ip_address(item):
                return True
        except ValueError:
            continue
    return False

@dataclass
class VerificationResult:
    ok: bool
    credential: AdminServiceCredential | None = None
    decision: str = AdminRequestAudit.Decision.DENIED
    error: str = ""
    body_hash: str = ""

def get_client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")

def verify_admin_request(request, max_skew_seconds=None):
    max_skew_seconds = max_skew_seconds or getattr(settings, "ADMIN_INTEGRATION_MAX_CLOCK_SKEW_SECONDS", 300)
    raw_key = request.headers.get("X-Admin-Service-Key", "")
    timestamp = request.headers.get("X-Admin-Timestamp", "")
    nonce = request.headers.get("X-Admin-Nonce", "")
    signature = request.headers.get("X-Admin-Signature", "")
    if not raw_key or not timestamp or not nonce or not signature:
        return VerificationResult(False, decision=AdminRequestAudit.Decision.UNSIGNED, error="missing admin signing headers")
    if not raw_key.startswith("adm_"):
        return VerificationResult(False, error="invalid admin key prefix")
    try:
        ts = int(timestamp)
    except ValueError:
        return VerificationResult(False, error="invalid timestamp")
    if abs(int(time.time()) - ts) > max_skew_seconds:
        return VerificationResult(False, error="timestamp outside allowed skew")
    credential = AdminServiceCredential.objects.filter(key_prefix=raw_key[:20], is_active=True).first()
    if not credential or credential.is_expired:
        return VerificationResult(False, error="credential not found or expired")
    if not credential.verify_key(raw_key):
        return VerificationResult(False, credential=credential, error="invalid admin service key")
    if not ip_allowed(get_client_ip(request), credential.allowed_ips):
        return VerificationResult(False, credential=credential, error="source ip not allowed")
    b_hash = body_sha256(request.body)
    expected = sign_request(credential.signing_secret, request.method, request.path, timestamp, nonce, b_hash)
    if not hmac.compare_digest(signature or "", expected or ""):
        return VerificationResult(False, credential=credential, error="invalid request signature", body_hash=b_hash)
    credential.mark_used()
    return VerificationResult(True, credential=credential, decision=AdminRequestAudit.Decision.ALLOWED, body_hash=b_hash)

def create_admin_service_credential(name, scopes, created_by=None, allowed_ips=None, expires_at=None):
    raw_key = generate_admin_api_key()
    signing_secret = generate_signing_secret()
    credential = AdminServiceCredential.objects.create(
        name=name,
        key_prefix=raw_key[:20],
        key_hash=make_password(raw_key),
        signing_key_id=f"askid_{secrets.token_hex(12)}",
        signing_secret=signing_secret,
        scopes=scopes,
        allowed_ips=allowed_ips or [],
        expires_at=expires_at,
        created_by=created_by,
    )
    return credential, raw_key, signing_secret

def rotate_admin_service_credential(credential):
    raw_key = generate_admin_api_key()
    signing_secret = generate_signing_secret()
    credential.key_prefix = raw_key[:20]
    credential.key_hash = make_password(raw_key)
    credential.signing_key_id = f"askid_{secrets.token_hex(12)}"
    credential.signing_secret = signing_secret
    credential.rotated_at = timezone.now()
    credential.save(update_fields=["key_prefix", "key_hash", "signing_key_id", "signing_secret", "rotated_at", "updated_at"])
    return raw_key, signing_secret

def seed_admin_integration_catalogues():
    for code, description in DEFAULT_ADMIN_SCOPES.items():
        AdminApiScope.objects.get_or_create(code=code, defaults={"title": code, "description": description})
    for domain, method, path, scope, description in DEFAULT_ADMIN_CONTRACT:
        AdminApiContractEndpoint.objects.get_or_create(method=method, path=path, defaults={"domain": domain, "required_scope": scope, "description": description})

def build_readiness_snapshot(created_by=None, persist=True):
    seed_admin_integration_catalogues()
    active_credentials = AdminServiceCredential.objects.filter(is_active=True).count()
    scopes = AdminApiScope.objects.filter(enabled=True).count()
    contract = AdminApiContractEndpoint.objects.filter(enabled=True).count()
    has_signing = AdminServiceCredential.objects.filter(is_active=True).exclude(signing_secret="").exists()
    checks = [
        {"code": "active_admin_service_credential", "ok": active_credentials > 0, "detail": f"{active_credentials} active admin service credentials"},
        {"code": "admin_api_scope_catalog", "ok": scopes >= len(DEFAULT_ADMIN_SCOPES), "detail": f"{scopes} enabled admin scopes"},
        {"code": "admin_api_contract", "ok": contract >= len(DEFAULT_ADMIN_CONTRACT), "detail": f"{contract} documented admin-control endpoints"},
        {"code": "request_signing", "ok": has_signing, "detail": "active credential has signing material"},
        {"code": "audit_middleware", "ok": "admin_integration.middleware.AdminOriginAuditMiddleware" in getattr(settings, "MIDDLEWARE", []), "detail": "admin-origin audit middleware configured"},
        {"code": "clock_skew", "ok": getattr(settings, "ADMIN_INTEGRATION_MAX_CLOCK_SKEW_SECONDS", 0) <= 300, "detail": "request signature timestamp skew is bounded"},
    ]
    status = "ready" if all(c["ok"] for c in checks) else "needs_attention"
    data = {"status": status, "checks": checks, "metadata": {"version": "39.0.0", "integration": "admin-control-platform"}}
    if persist:
        AdminIntegrationReadinessSnapshot.objects.create(status=status, checks=checks, metadata=data["metadata"], created_by=created_by)
    return data
