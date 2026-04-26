import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from .models import IdentityAssuranceEvent, PasskeyChallenge, PasskeyCredential, StepUpPolicy, StepUpSession, TrustedDevice


def _hash_secret(value: str) -> str:
    return hashlib.sha256((settings.SECRET_KEY + value).encode("utf-8")).hexdigest()


def issue_passkey_challenge(*, user=None, organization=None, purpose, rp_id, origin="", lifetime_minutes=5, metadata=None):
    raw_challenge = secrets.token_urlsafe(48)
    challenge = PasskeyChallenge.objects.create(
        user=user,
        organization=organization,
        purpose=purpose,
        challenge_prefix=raw_challenge[:16],
        challenge_hash=_hash_secret(raw_challenge),
        rp_id=rp_id,
        origin=origin,
        expires_at=timezone.now() + timedelta(minutes=lifetime_minutes),
        metadata=metadata or {},
    )
    return challenge, raw_challenge


def consume_passkey_challenge(raw_challenge: str, *, purpose=None):
    hashed = _hash_secret(raw_challenge)
    query = PasskeyChallenge.objects.filter(challenge_hash=hashed)
    if purpose:
        query = query.filter(purpose=purpose)
    challenge = query.first()
    if not challenge or not challenge.is_usable:
        return None
    challenge.consume()
    return challenge


def register_passkey_metadata(*, user, raw_credential_id, public_key_jwk, label="", organization=None, platform="unknown", transports=None, attestation_type="", aaguid="", metadata=None):
    credential_id_hash = _hash_secret(raw_credential_id)
    credential, created = PasskeyCredential.objects.update_or_create(
        credential_id_hash=credential_id_hash,
        defaults={
            "user": user,
            "organization": organization,
            "label": label,
            "credential_id_prefix": raw_credential_id[:16],
            "public_key_jwk": public_key_jwk or {},
            "platform": platform or PasskeyCredential.Platform.UNKNOWN,
            "transports": transports or [],
            "attestation_type": attestation_type,
            "aaguid": aaguid,
            "status": PasskeyCredential.Status.ACTIVE,
        },
    )
    record_identity_event(user=user, organization=organization, event_type="passkey.registered", result="success", method="passkey", metadata={"created": created, **(metadata or {})})
    return credential


def remember_trusted_device(*, user, raw_device_id, name, platform="unknown", organization=None, trust_level="standard", request=None, expires_at=None, metadata=None):
    device_hash = _hash_secret(raw_device_id)
    defaults = {
        "user": user,
        "organization": organization,
        "name": name,
        "device_prefix": raw_device_id[:16],
        "platform": platform or TrustedDevice.Platform.UNKNOWN,
        "trust_level": trust_level,
        "status": TrustedDevice.Status.ACTIVE,
        "expires_at": expires_at,
        "metadata": metadata or {},
        "last_seen_at": timezone.now(),
    }
    if request:
        defaults["last_seen_ip"] = request.META.get("REMOTE_ADDR")
        defaults["last_seen_user_agent"] = request.META.get("HTTP_USER_AGENT", "")[:1000]
    device, created = TrustedDevice.objects.update_or_create(device_hash=device_hash, defaults=defaults)
    record_identity_event(user=user, organization=organization, event_type="trusted_device.remembered", result="success", method="device", request=request, metadata={"created": created})
    return device


def satisfy_step_up(*, user, trigger, method, organization=None, max_age_seconds=900, risk_score=0, request=None, metadata=None):
    session = StepUpSession.objects.create(
        user=user,
        organization=organization,
        trigger=trigger,
        method=method,
        risk_score=risk_score,
        expires_at=timezone.now() + timedelta(seconds=max_age_seconds),
        metadata=metadata or {},
    )
    record_identity_event(user=user, organization=organization, event_type="step_up.satisfied", result="success", method=method, risk_score=risk_score, request=request, metadata={"trigger": trigger})
    return session


def has_recent_step_up(*, user, trigger, organization=None, required_method=None):
    qs = StepUpSession.objects.filter(user=user, trigger=trigger, expires_at__gt=timezone.now(), revoked_at__isnull=True)
    if organization:
        qs = qs.filter(organization=organization)
    if required_method and required_method != StepUpPolicy.RequiredMethod.ANY_STRONG:
        qs = qs.filter(method=required_method)
    return qs.exists()


def record_identity_event(*, event_type, result, user=None, organization=None, method="", risk_score=0, request=None, metadata=None):
    event_data = {
        "user": user,
        "organization": organization,
        "event_type": event_type,
        "result": result,
        "method": method,
        "risk_score": risk_score,
        "metadata": metadata or {},
    }
    if request:
        event_data["ip_address"] = request.META.get("REMOTE_ADDR")
        event_data["user_agent"] = request.META.get("HTTP_USER_AGENT", "")[:1000]
    return IdentityAssuranceEvent.objects.create(**event_data)
