import time

from .models import AdminRequestAudit
from .services import body_sha256, get_client_ip, verify_admin_request


class AdminOriginAuditMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.monotonic()
        is_admin_origin = bool(request.headers.get("X-Admin-Service-Key") or request.headers.get("X-Admin-Signature"))
        result = None
        if is_admin_origin:
            result = verify_admin_request(request)
            request.admin_integration_verification = result
        response = self.get_response(request)
        if is_admin_origin:
            try:
                AdminRequestAudit.objects.create(
                    credential=result.credential if result else None,
                    key_prefix=(request.headers.get("X-Admin-Service-Key", "") or "")[:20],
                    method=request.method,
                    path=request.path,
                    query_string_hash=body_sha256(request.META.get("QUERY_STRING", "").encode("utf-8")),
                    body_hash=result.body_hash if result and result.body_hash else body_sha256(request.body),
                    nonce=request.headers.get("X-Admin-Nonce", ""),
                    timestamp=request.headers.get("X-Admin-Timestamp", ""),
                    ip_address=get_client_ip(request),
                    user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
                    decision=result.decision if result else AdminRequestAudit.Decision.UNSIGNED,
                    status_code=getattr(response, "status_code", None),
                    latency_ms=int((time.monotonic() - start) * 1000),
                    error=result.error if result else "",
                )
            except Exception:
                pass
        return response
