import hashlib
import secrets
from datetime import timedelta
from urllib.parse import urlencode

from django.conf import settings
from django.utils import timezone

from .models import AccountToken


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def issue_account_token(user, purpose: str, lifetime: timedelta) -> str:
    raw_token = secrets.token_urlsafe(48)
    token_hash = hash_token(raw_token)
    expires_at = timezone.now() + lifetime

    AccountToken.objects.filter(user=user, purpose=purpose, used_at__isnull=True).update(used_at=timezone.now())
    AccountToken.objects.create(user=user, purpose=purpose, token_hash=token_hash, expires_at=expires_at)
    return raw_token


def get_valid_account_token(raw_token: str, purpose: str) -> AccountToken | None:
    token_hash = hash_token(raw_token)
    try:
        token = AccountToken.objects.select_related("user").get(token_hash=token_hash, purpose=purpose)
    except AccountToken.DoesNotExist:
        return None
    if token.is_used or token.is_expired:
        return None
    if not token.user.is_active:
        return None
    return token


def build_action_url(base_url: str, token: str, extra_params: dict | None = None) -> str:
    params = {"token": token}
    if extra_params:
        params.update(extra_params)
    separator = "&" if "?" in base_url else "?"
    return f"{base_url}{separator}{urlencode(params)}"
