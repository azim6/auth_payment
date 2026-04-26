import hashlib
from datetime import datetime, timezone as dt_timezone

from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from .models import AuthSessionDevice, RefreshTokenFamily


def request_ip(request) -> str | None:
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def hash_session_key(session_key: str) -> str:
    return hashlib.sha256(session_key.encode("utf-8")).hexdigest()


def label_from_user_agent(user_agent: str) -> str:
    lowered = user_agent.lower()
    if "android" in lowered:
        return "Android device"
    if "windows" in lowered:
        return "Windows device"
    if "iphone" in lowered or "ipad" in lowered:
        return "iOS device"
    if "mac os" in lowered or "macintosh" in lowered:
        return "macOS browser"
    if "linux" in lowered:
        return "Linux browser"
    return "Web browser" if user_agent else "Unknown device"


def record_session_device(request, user) -> AuthSessionDevice | None:
    session_key = request.session.session_key
    if not session_key:
        request.session.save()
        session_key = request.session.session_key
    if not session_key:
        return None
    user_agent = request.META.get("HTTP_USER_AGENT", "")[:2000]
    device, _created = AuthSessionDevice.objects.update_or_create(
        user=user,
        session_key_hash=hash_session_key(session_key),
        defaults={
            "label": label_from_user_agent(user_agent),
            "user_agent": user_agent,
            "ip_address": request_ip(request),
            "last_seen_at": timezone.now(),
            "revoked_at": None,
        },
    )
    return device


def refresh_expires_at(refresh: RefreshToken):
    return datetime.fromtimestamp(int(refresh.payload["exp"]), tz=dt_timezone.utc)


def record_refresh_family(refresh: RefreshToken, user, request=None, client_id: str = "") -> RefreshTokenFamily | None:
    jti = refresh.payload.get("jti")
    if not jti:
        return None
    user_agent = request.META.get("HTTP_USER_AGENT", "")[:2000] if request else ""
    ip_address = request_ip(request) if request else None
    record, _created = RefreshTokenFamily.objects.update_or_create(
        jti=jti,
        defaults={
            "user": user,
            "client_id": client_id,
            "user_agent": user_agent,
            "ip_address": ip_address,
            "expires_at": refresh_expires_at(refresh),
            "last_seen_at": timezone.now(),
        },
    )
    return record


def revoke_all_refresh_families_for_user(user) -> int:
    return RefreshTokenFamily.objects.filter(user=user, revoked_at__isnull=True).update(revoked_at=timezone.now())
