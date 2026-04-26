import secrets
from dataclasses import dataclass

import pyotp
from django.conf import settings
from django.core import signing
from django.contrib.auth.hashers import check_password, make_password
from django.utils import timezone

RECOVERY_CODE_COUNT = 10
RECOVERY_CODE_BYTES = 5


@dataclass(frozen=True)
class TotpSetup:
    secret: str
    provisioning_uri: str


def generate_totp_secret() -> str:
    return pyotp.random_base32()


def sign_secret(secret: str) -> str:
    return signing.dumps(secret, salt="accounts.mfa.totp")


def unsign_secret(value: str) -> str:
    return signing.loads(value, salt="accounts.mfa.totp")


def build_totp_uri(user, secret: str) -> str:
    issuer = getattr(settings, "MFA_TOTP_ISSUER", "Django Auth Platform")
    return pyotp.totp.TOTP(secret).provisioning_uri(name=user.email, issuer_name=issuer)


def verify_totp(secret: str, code: str) -> bool:
    if not code:
        return False
    normalized = str(code).strip().replace(" ", "")
    return pyotp.TOTP(secret).verify(normalized, valid_window=1)


def generate_recovery_codes() -> list[str]:
    codes = []
    for _ in range(RECOVERY_CODE_COUNT):
        raw = secrets.token_hex(RECOVERY_CODE_BYTES).upper()
        codes.append(f"{raw[:5]}-{raw[5:]}")
    return codes


def hash_recovery_code(code: str) -> str:
    return make_password(normalize_recovery_code(code))


def normalize_recovery_code(code: str) -> str:
    return str(code).strip().replace("-", "").replace(" ", "").upper()


def recovery_code_matches(raw_code: str, encoded_hash: str) -> bool:
    return check_password(normalize_recovery_code(raw_code), encoded_hash)


def now():
    return timezone.now()
