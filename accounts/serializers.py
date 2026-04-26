from django.contrib.auth import authenticate, login
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken, TokenError

from .mfa import (
    build_totp_uri,
    generate_recovery_codes,
    generate_totp_secret,
    hash_recovery_code,
    recovery_code_matches,
    sign_secret,
    unsign_secret,
    verify_totp,
)
from .models import (
    AccountDeletionRequest,
    AccountToken,
    AuditLog,
    AuthSessionDevice,
    AuthorizationCode,
    DataExportRequest,
    MfaDevice,
    OAuthClient,
    OAuthTokenActivity,
    PrivacyPreference,
    RecoveryCode,
    RefreshTokenFamily,
    ServiceCredential,
    User,
    UserConsent,
)
from .services import queue_email_verification, queue_password_reset
from .tokens import get_valid_account_token
from .oauth import (
    build_redirect_uri,
    create_authorization_code,
    find_valid_authorization_code,
    generate_client_id,
    generate_client_secret,
    hash_client_secret,
    introspect_token,
    issue_client_tokens,
    issue_service_access_token,
    revoke_token,
    verify_client_secret,
    verify_pkce,
)
from .service_credentials import (
    find_valid_service_credential,
    generate_service_key,
    hash_service_key,
    service_key_prefix,
    validate_service_scopes,
)
from .device_security import record_refresh_family, record_session_device, revoke_all_refresh_families_for_user
from .privacy import (
    build_user_export_payload,
    cancel_account_deletion,
    confirm_account_deletion,
    create_account_deletion_request,
    create_data_export_request,
    get_or_create_privacy_preferences,
    record_consent,
)


class UserPublicSerializer(serializers.ModelSerializer):
    public_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "display_name", "public_name", "avatar_url", "bio", "created_at"]
        read_only_fields = fields


class UserPrivateSerializer(serializers.ModelSerializer):
    mfa_enabled = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "username",
            "display_name",
            "avatar_url",
            "bio",
            "email_verified",
            "mfa_enabled",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "email", "username", "email_verified", "mfa_enabled", "is_active", "created_at", "updated_at"]

    def get_mfa_enabled(self, obj):
        return MfaDevice.objects.filter(user=obj, confirmed_at__isnull=False).exists()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=12, trim_whitespace=False)
    password_confirm = serializers.CharField(write_only=True, trim_whitespace=False)

    class Meta:
        model = User
        fields = ["id", "email", "username", "display_name", "password", "password_confirm"]
        read_only_fields = ["id"]

    def validate_email(self, value):
        email = value.lower().strip()
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return email

    def validate_username(self, value):
        username = value.strip()
        if User.objects.filter(username__iexact=username).exists():
            raise serializers.ValidationError("A user with this username already exists.")
        return username

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        validate_password(attrs["password"])
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        validated_data.pop("password_confirm")
        password = validated_data.pop("password")
        user = User.objects.create_user(password=password, **validated_data)
        transaction.on_commit(lambda: queue_email_verification(user))
        return user


class MfaLoginMixin:
    def validate_mfa(self, user, otp=None, recovery_code=None):
        device = MfaDevice.objects.filter(user=user, confirmed_at__isnull=False).first()
        if not device:
            return
        if otp:
            secret = unsign_secret(device.secret)
            if verify_totp(secret, otp):
                device.mark_used()
                return
        if recovery_code:
            usable_codes = RecoveryCode.objects.filter(user=user, used_at__isnull=True)
            for code in usable_codes:
                if recovery_code_matches(recovery_code, code.code_hash):
                    code.mark_used()
                    device.mark_used()
                    return
        raise serializers.ValidationError({"mfa": "A valid authenticator code or recovery code is required."})


class SessionLoginSerializer(MfaLoginMixin, serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    otp = serializers.CharField(write_only=True, required=False, allow_blank=True, trim_whitespace=False)
    recovery_code = serializers.CharField(write_only=True, required=False, allow_blank=True, trim_whitespace=False)

    def validate(self, attrs):
        request = self.context.get("request")
        email = attrs["email"].lower().strip()
        password = attrs["password"]
        user = authenticate(request=request, username=email, password=password)
        if not user:
            raise serializers.ValidationError("Invalid email or password.")
        if not user.is_active:
            raise serializers.ValidationError("This account is disabled.")
        self.validate_mfa(user, attrs.get("otp"), attrs.get("recovery_code"))
        attrs["user"] = user
        return attrs

    def login(self):
        request = self.context["request"]
        user = self.validated_data["user"]
        login(request, user)
        User.objects.filter(pk=user.pk).update(last_seen_at=timezone.now())
        record_session_device(request, user)
        return user


class TokenLoginSerializer(MfaLoginMixin, serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    otp = serializers.CharField(write_only=True, required=False, allow_blank=True, trim_whitespace=False)
    recovery_code = serializers.CharField(write_only=True, required=False, allow_blank=True, trim_whitespace=False)

    def validate(self, attrs):
        request = self.context.get("request")
        email = attrs["email"].lower().strip()
        password = attrs["password"]
        user = authenticate(request=request, username=email, password=password)
        if not user:
            raise serializers.ValidationError("Invalid email or password.")
        if not user.is_active:
            raise serializers.ValidationError("This account is disabled.")
        self.validate_mfa(user, attrs.get("otp"), attrs.get("recovery_code"))
        refresh = RefreshToken.for_user(user)
        User.objects.filter(pk=user.pk).update(last_seen_at=timezone.now())
        record_refresh_family(refresh, user, request=request)
        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": UserPrivateSerializer(user).data,
        }


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()

    def validate(self, attrs):
        self.token = attrs["refresh"]
        return attrs

    def save(self, **kwargs):
        try:
            RefreshToken(self.token).blacklist()
        except TokenError as exc:
            raise serializers.ValidationError("Invalid or expired refresh token.") from exc


class ResendEmailVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def save(self, **kwargs):
        email = self.validated_data["email"].lower().strip()
        user = User.objects.filter(email=email, is_active=True).first()
        if user and not user.email_verified:
            queue_email_verification(user)
        return {"detail": "If the account exists and needs verification, an email has been sent."}


class ConfirmEmailSerializer(serializers.Serializer):
    token = serializers.CharField(trim_whitespace=False)

    def validate_token(self, value):
        token = get_valid_account_token(value, AccountToken.Purpose.EMAIL_VERIFICATION)
        if not token:
            raise serializers.ValidationError("Invalid or expired verification token.")
        return value

    @transaction.atomic
    def save(self, **kwargs):
        token = get_valid_account_token(self.validated_data["token"], AccountToken.Purpose.EMAIL_VERIFICATION)
        if not token:
            raise serializers.ValidationError("Invalid or expired verification token.")
        User.objects.filter(pk=token.user.pk).update(email_verified=True)
        token.mark_used()
        return token.user


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def save(self, **kwargs):
        email = self.validated_data["email"].lower().strip()
        user = User.objects.filter(email=email, is_active=True).first()
        if user:
            queue_password_reset(user)
        return {"detail": "If the account exists, a password reset email has been sent."}


class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField(trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, min_length=12, trim_whitespace=False)
    new_password_confirm = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError({"new_password_confirm": "Passwords do not match."})
        token = get_valid_account_token(attrs["token"], AccountToken.Purpose.PASSWORD_RESET)
        if not token:
            raise serializers.ValidationError({"token": "Invalid or expired password reset token."})
        validate_password(attrs["new_password"], user=token.user)
        attrs["account_token"] = token
        return attrs

    @transaction.atomic
    def save(self, **kwargs):
        token = self.validated_data["account_token"]
        user = token.user
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password", "updated_at"])
        token.mark_used()
        return user


class MfaStatusSerializer(serializers.Serializer):
    enabled = serializers.BooleanField()
    recovery_codes_remaining = serializers.IntegerField()


class MfaStartSetupSerializer(serializers.Serializer):
    name = serializers.CharField(required=False, allow_blank=True, max_length=120)

    @transaction.atomic
    def save(self, **kwargs):
        user = self.context["request"].user
        secret = generate_totp_secret()
        device, _ = MfaDevice.objects.update_or_create(
            user=user,
            defaults={
                "name": self.validated_data.get("name") or "Authenticator app",
                "secret": sign_secret(secret),
                "confirmed_at": None,
                "last_used_at": None,
            },
        )
        return {
            "device_id": str(device.id),
            "secret": secret,
            "provisioning_uri": build_totp_uri(user, secret),
            "detail": "Scan the provisioning URI with an authenticator app, then confirm with a current code.",
        }


class MfaConfirmSetupSerializer(serializers.Serializer):
    otp = serializers.CharField(trim_whitespace=False)

    @transaction.atomic
    def validate(self, attrs):
        user = self.context["request"].user
        device = MfaDevice.objects.filter(user=user).first()
        if not device:
            raise serializers.ValidationError("Start MFA setup before confirming it.")
        secret = unsign_secret(device.secret)
        if not verify_totp(secret, attrs["otp"]):
            raise serializers.ValidationError({"otp": "Invalid authenticator code."})
        attrs["device"] = device
        return attrs

    @transaction.atomic
    def save(self, **kwargs):
        user = self.context["request"].user
        device = self.validated_data["device"]
        device.mark_confirmed()
        RecoveryCode.objects.filter(user=user).delete()
        raw_codes = generate_recovery_codes()
        RecoveryCode.objects.bulk_create([
            RecoveryCode(user=user, code_hash=hash_recovery_code(code)) for code in raw_codes
        ])
        return {
            "detail": "MFA is enabled. Store these recovery codes securely; they are shown only once.",
            "recovery_codes": raw_codes,
        }


class MfaDisableSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    otp = serializers.CharField(write_only=True, required=False, allow_blank=True, trim_whitespace=False)
    recovery_code = serializers.CharField(write_only=True, required=False, allow_blank=True, trim_whitespace=False)

    def validate(self, attrs):
        request = self.context["request"]
        user = request.user
        if not user.check_password(attrs["password"]):
            raise serializers.ValidationError({"password": "Invalid password."})
        MfaLoginMixin().validate_mfa(user, attrs.get("otp"), attrs.get("recovery_code"))
        return attrs

    @transaction.atomic
    def save(self, **kwargs):
        user = self.context["request"].user
        MfaDevice.objects.filter(user=user).delete()
        RecoveryCode.objects.filter(user=user).delete()
        return {"detail": "MFA has been disabled."}


class MfaRegenerateRecoveryCodesSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    otp = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        user = self.context["request"].user
        if not user.check_password(attrs["password"]):
            raise serializers.ValidationError({"password": "Invalid password."})
        device = MfaDevice.objects.filter(user=user, confirmed_at__isnull=False).first()
        if not device:
            raise serializers.ValidationError("MFA is not enabled.")
        secret = unsign_secret(device.secret)
        if not verify_totp(secret, attrs["otp"]):
            raise serializers.ValidationError({"otp": "Invalid authenticator code."})
        attrs["device"] = device
        return attrs

    @transaction.atomic
    def save(self, **kwargs):
        user = self.context["request"].user
        RecoveryCode.objects.filter(user=user).delete()
        raw_codes = generate_recovery_codes()
        RecoveryCode.objects.bulk_create([
            RecoveryCode(user=user, code_hash=hash_recovery_code(code)) for code in raw_codes
        ])
        self.validated_data["device"].mark_used()
        return {
            "detail": "Recovery codes have been regenerated. Store these securely; they are shown only once.",
            "recovery_codes": raw_codes,
        }


class OAuthClientSerializer(serializers.ModelSerializer):
    redirect_uris = serializers.ListField(child=serializers.CharField(max_length=500), write_only=True)
    redirect_uri_list = serializers.ListField(child=serializers.CharField(max_length=500), read_only=True)
    client_secret = serializers.CharField(read_only=True)

    class Meta:
        model = OAuthClient
        fields = [
            "id",
            "name",
            "client_id",
            "client_secret",
            "is_confidential",
            "is_active",
            "redirect_uris",
            "redirect_uri_list",
            "allowed_scopes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "client_id", "client_secret", "is_active", "redirect_uri_list", "created_at", "updated_at"]

    def validate_allowed_scopes(self, value):
        requested = {scope for scope in value.split() if scope}
        allowed = {"openid", "profile", "email", "offline_access"}
        unknown = requested - allowed
        if unknown:
            raise serializers.ValidationError(f"Unsupported scopes: {', '.join(sorted(unknown))}")
        if "openid" not in requested:
            raise serializers.ValidationError("OIDC clients must include the openid scope.")
        return " ".join(sorted(requested))

    def create(self, validated_data):
        redirect_uris = validated_data.pop("redirect_uris")
        raw_secret = generate_client_secret() if validated_data.get("is_confidential", True) else ""
        client = OAuthClient.objects.create(
            owner=self.context["request"].user,
            client_id=generate_client_id(),
            client_secret_hash=hash_client_secret(raw_secret) if raw_secret else "",
            redirect_uris="\n".join(redirect_uris),
            **validated_data,
        )
        client.client_secret = raw_secret
        return client


class OAuthAuthorizeSerializer(serializers.Serializer):
    response_type = serializers.ChoiceField(choices=["code"])
    client_id = serializers.CharField()
    redirect_uri = serializers.CharField(max_length=500)
    scope = serializers.CharField(required=False, allow_blank=True, default="openid profile email")
    state = serializers.CharField(required=False, allow_blank=True, max_length=255)
    nonce = serializers.CharField(required=False, allow_blank=True, max_length=255)
    code_challenge = serializers.CharField(required=False, allow_blank=True, max_length=255)
    code_challenge_method = serializers.ChoiceField(required=False, choices=["plain", "S256"], allow_blank=True)

    def validate(self, attrs):
        client = OAuthClient.objects.filter(client_id=attrs["client_id"], is_active=True).first()
        if not client:
            raise serializers.ValidationError({"client_id": "Unknown or inactive client."})
        if attrs["redirect_uri"] not in client.redirect_uri_list:
            raise serializers.ValidationError({"redirect_uri": "Redirect URI is not registered for this client."})
        requested_scopes = {scope for scope in attrs.get("scope", "").split() if scope}
        if not requested_scopes:
            requested_scopes = {"openid"}
        unsupported = requested_scopes - client.scope_set
        if unsupported:
            raise serializers.ValidationError({"scope": f"Unsupported scopes: {', '.join(sorted(unsupported))}"})
        if "openid" not in requested_scopes:
            raise serializers.ValidationError({"scope": "OIDC authorization requests must include openid."})
        if attrs.get("code_challenge") and not attrs.get("code_challenge_method"):
            attrs["code_challenge_method"] = "plain"
        attrs["client"] = client
        attrs["scope"] = " ".join(sorted(requested_scopes))
        return attrs

    @transaction.atomic
    def save(self, **kwargs):
        user = self.context["request"].user
        raw_code, _code = create_authorization_code(
            client=self.validated_data["client"],
            user=user,
            redirect_uri=self.validated_data["redirect_uri"],
            scope=self.validated_data["scope"],
            state=self.validated_data.get("state", ""),
            nonce=self.validated_data.get("nonce", ""),
            code_challenge=self.validated_data.get("code_challenge", ""),
            code_challenge_method=self.validated_data.get("code_challenge_method", ""),
        )
        return {
            "code": raw_code,
            "redirect_to": build_redirect_uri(
                self.validated_data["redirect_uri"],
                code=raw_code,
                state=self.validated_data.get("state", ""),
            ),
        }


class OAuthTokenExchangeSerializer(serializers.Serializer):
    grant_type = serializers.ChoiceField(choices=["authorization_code"])
    code = serializers.CharField(trim_whitespace=False)
    redirect_uri = serializers.CharField(max_length=500)
    client_id = serializers.CharField()
    client_secret = serializers.CharField(required=False, allow_blank=True, trim_whitespace=False)
    code_verifier = serializers.CharField(required=False, allow_blank=True, trim_whitespace=False)

    def validate(self, attrs):
        code = find_valid_authorization_code(attrs["code"])
        if not code or code.is_expired:
            raise serializers.ValidationError({"code": "Invalid or expired authorization code."})
        client = code.client
        if client.client_id != attrs["client_id"] or not client.is_active:
            raise serializers.ValidationError({"client_id": "Client does not match the authorization code."})
        if attrs["redirect_uri"] != code.redirect_uri:
            raise serializers.ValidationError({"redirect_uri": "Redirect URI does not match the authorization request."})
        if client.is_confidential and not verify_client_secret(attrs.get("client_secret", ""), client.client_secret_hash):
            raise serializers.ValidationError({"client_secret": "Invalid client secret."})
        if not verify_pkce(
            verifier=attrs.get("code_verifier", ""),
            challenge=code.code_challenge,
            method=code.code_challenge_method,
        ):
            raise serializers.ValidationError({"code_verifier": "Invalid PKCE verifier."})
        attrs["authorization_code"] = code
        return attrs

    @transaction.atomic
    def save(self, **kwargs):
        code = self.validated_data["authorization_code"]
        tokens = issue_client_tokens(user=code.user, client=code.client, scope=code.scope, nonce=code.nonce)
        code.mark_used()
        return tokens


class ServiceCredentialSerializer(serializers.ModelSerializer):
    raw_key = serializers.CharField(read_only=True)
    scopes = serializers.CharField(default="users:read tokens:introspect")

    class Meta:
        model = ServiceCredential
        fields = [
            "id", "name", "key_prefix", "raw_key", "scopes", "is_active",
            "last_used_at", "expires_at", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "key_prefix", "raw_key", "is_active", "last_used_at", "created_at", "updated_at"]

    def validate_scopes(self, value):
        try:
            return validate_service_scopes(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc

    def create(self, validated_data):
        raw_key = generate_service_key()
        credential = ServiceCredential.objects.create(
            owner=self.context["request"].user,
            key_prefix=service_key_prefix(raw_key),
            key_hash=hash_service_key(raw_key),
            **validated_data,
        )
        credential.raw_key = raw_key
        return credential


class ServiceTokenSerializer(serializers.Serializer):
    grant_type = serializers.ChoiceField(choices=["client_credentials"])
    service_key = serializers.CharField(write_only=True, trim_whitespace=False)
    scope = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        credential = find_valid_service_credential(attrs["service_key"])
        if not credential:
            raise serializers.ValidationError({"service_key": "Invalid, expired, or inactive service key."})
        requested = {scope for scope in attrs.get("scope", "").split() if scope}
        if requested:
            missing = requested - credential.scope_set
            if missing:
                raise serializers.ValidationError({"scope": f"Unsupported service scopes: {', '.join(sorted(missing))}"})
            credential.scopes = " ".join(sorted(requested))
        attrs["credential"] = credential
        return attrs

    def save(self, **kwargs):
        return issue_service_access_token(credential=self.validated_data["credential"])


class TokenIntrospectionSerializer(serializers.Serializer):
    token = serializers.CharField(write_only=True, trim_whitespace=False)

    def save(self, **kwargs):
        return introspect_token(self.validated_data["token"])


class TokenRevocationSerializer(serializers.Serializer):
    token = serializers.CharField(write_only=True, trim_whitespace=False)

    def save(self, **kwargs):
        return {"revoked": revoke_token(self.validated_data["token"])}


class AuditLogSerializer(serializers.ModelSerializer):
    actor_email = serializers.EmailField(source="actor.email", read_only=True)

    class Meta:
        model = AuditLog
        fields = [
            "id", "actor", "actor_email", "category", "action", "outcome",
            "ip_address", "user_agent", "request_id", "client_id", "subject_user_id",
            "metadata", "created_at",
        ]
        read_only_fields = fields


class OAuthTokenActivitySerializer(serializers.ModelSerializer):
    client_id = serializers.CharField(source="client.client_id", read_only=True)
    service_name = serializers.CharField(source="service_credential.name", read_only=True)
    user_email = serializers.EmailField(source="user.email", read_only=True)
    active = serializers.BooleanField(source="is_active", read_only=True)

    class Meta:
        model = OAuthTokenActivity
        fields = [
            "id", "jti", "token_type", "user", "user_email", "client", "client_id",
            "service_credential", "service_name", "scope", "active", "expires_at",
            "revoked_at", "created_at", "last_seen_at", "metadata",
        ]
        read_only_fields = fields



class AuthSessionDeviceSerializer(serializers.ModelSerializer):
    active = serializers.BooleanField(source="is_active", read_only=True)

    class Meta:
        model = AuthSessionDevice
        fields = [
            "id", "label", "active", "ip_address", "user_agent",
            "last_seen_at", "revoked_at", "created_at", "updated_at",
        ]
        read_only_fields = fields


class RefreshTokenFamilySerializer(serializers.ModelSerializer):
    active = serializers.BooleanField(source="is_active", read_only=True)

    class Meta:
        model = RefreshTokenFamily
        fields = [
            "id", "jti", "client_id", "active", "ip_address", "user_agent",
            "expires_at", "revoked_at", "created_at", "last_seen_at", "metadata",
        ]
        read_only_fields = fields


class RevokeAllRefreshTokensSerializer(serializers.Serializer):
    def save(self, **kwargs):
        user = self.context["request"].user
        count = revoke_all_refresh_families_for_user(user)
        return {"revoked": count}


class ServiceCredentialRotateSerializer(serializers.Serializer):
    raw_key = serializers.CharField(read_only=True)
    key_prefix = serializers.CharField(read_only=True)

    def save(self, **kwargs):
        credential = self.context["credential"]
        raw_key = generate_service_key()
        credential.key_prefix = service_key_prefix(raw_key)
        credential.key_hash = hash_service_key(raw_key)
        credential.last_used_at = None
        credential.save(update_fields=["key_prefix", "key_hash", "last_used_at", "updated_at"])
        return {"raw_key": raw_key, "key_prefix": credential.key_prefix}

class PrivacyPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrivacyPreference
        fields = [
            "analytics_consent",
            "marketing_email_consent",
            "product_email_consent",
            "profile_discoverable",
            "data_processing_region",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def validate_data_processing_region(self, value):
        value = value.strip().lower() or "default"
        allowed = {"default", "eu", "us", "apac"}
        if value not in allowed:
            raise serializers.ValidationError("Unsupported processing region.")
        return value


class UserConsentSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserConsent
        fields = [
            "id", "consent_type", "version", "granted", "source",
            "metadata", "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate_version(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Consent version is required.")
        return value

    def create(self, validated_data):
        request = self.context["request"]
        return record_consent(user=request.user, request=request, **validated_data)


class DataExportRequestSerializer(serializers.ModelSerializer):
    export_payload_preview = serializers.SerializerMethodField()

    class Meta:
        model = DataExportRequest
        fields = [
            "id", "status", "format", "download_url", "expires_at", "error",
            "completed_at", "created_at", "updated_at", "export_payload_preview",
        ]
        read_only_fields = fields

    def get_export_payload_preview(self, obj):
        if obj.status == DataExportRequest.Status.PENDING:
            return None
        return None


class DataExportCreateSerializer(serializers.Serializer):
    def save(self, **kwargs):
        request = self.context["request"]
        return create_data_export_request(user=request.user, request=request)


class DataExportPayloadSerializer(serializers.Serializer):
    def save(self, **kwargs):
        return build_user_export_payload(self.context["request"].user)


class AccountDeletionRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccountDeletionRequest
        fields = [
            "id", "status", "reason", "confirm_before", "scheduled_for",
            "confirmed_at", "cancelled_at", "completed_at", "created_at", "updated_at",
        ]
        read_only_fields = fields


class AccountDeletionCreateSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, max_length=2000)

    def save(self, **kwargs):
        request = self.context["request"]
        return create_account_deletion_request(
            user=request.user,
            reason=self.validated_data.get("reason", ""),
            request=request,
        )


class AccountDeletionConfirmSerializer(serializers.Serializer):
    deletion_request_id = serializers.UUIDField()

    def validate_deletion_request_id(self, value):
        request = self.context["request"]
        deletion = AccountDeletionRequest.objects.filter(id=value, user=request.user).first()
        if not deletion:
            raise serializers.ValidationError("Deletion request not found.")
        if not deletion.is_confirmable:
            raise serializers.ValidationError("Deletion request is not confirmable.")
        self.deletion = deletion
        return value

    def save(self, **kwargs):
        return confirm_account_deletion(deletion=self.deletion, request=self.context["request"])


class AccountDeletionCancelSerializer(serializers.Serializer):
    deletion_request_id = serializers.UUIDField()

    def validate_deletion_request_id(self, value):
        request = self.context["request"]
        deletion = AccountDeletionRequest.objects.filter(id=value, user=request.user).first()
        if not deletion:
            raise serializers.ValidationError("Deletion request not found.")
        self.deletion = deletion
        return value

    def save(self, **kwargs):
        return cancel_account_deletion(deletion=self.deletion, request=self.context["request"])



from .models import Organization, OrganizationInvitation, OrganizationMembership, PermissionPolicy, RolePermissionGrant, TenantServiceCredential
from .tenancy import (
    find_active_invitation,
    generate_invitation_token,
    generate_tenant_service_key,
    hash_invitation_token,
    hash_tenant_service_key,
    tenant_service_key_prefix,
    validate_tenant_service_scopes,
)


class OrganizationSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = [
            "id", "name", "slug", "plan", "is_active", "metadata",
            "role", "member_count", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "is_active", "role", "member_count", "created_at", "updated_at"]

    def get_role(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None
        membership = obj.memberships.filter(user=request.user, is_active=True).first()
        return membership.role if membership else None

    def get_member_count(self, obj):
        return obj.memberships.filter(is_active=True).count()

    def create(self, validated_data):
        request = self.context["request"]
        organization = Organization.objects.create(owner=request.user, **validated_data)
        OrganizationMembership.objects.create(
            organization=organization,
            user=request.user,
            role=OrganizationMembership.Role.OWNER,
            invited_by=request.user,
        )
        write_audit_event(
            request=request,
            actor=request.user,
            category=AuditLog.Category.ADMIN,
            action="organization.created",
            metadata={"organization_id": str(organization.id), "slug": organization.slug},
        )
        return organization


class OrganizationMembershipSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    display_name = serializers.CharField(source="user.public_name", read_only=True)

    class Meta:
        model = OrganizationMembership
        fields = [
            "id", "user", "user_email", "display_name", "role", "is_active",
            "joined_at", "updated_at",
        ]
        read_only_fields = ["id", "user", "user_email", "display_name", "joined_at", "updated_at"]


class OrganizationMembershipUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganizationMembership
        fields = ["role", "is_active"]

    def validate_role(self, value):
        if value == OrganizationMembership.Role.OWNER:
            raise serializers.ValidationError("Transfer ownership through an explicit owner-transfer workflow.")
        return value


class OrganizationInvitationSerializer(serializers.ModelSerializer):
    raw_token = serializers.CharField(read_only=True)
    organization_slug = serializers.CharField(source="organization.slug", read_only=True)

    class Meta:
        model = OrganizationInvitation
        fields = [
            "id", "organization", "organization_slug", "email", "role", "raw_token",
            "expires_at", "accepted_at", "revoked_at", "created_at",
        ]
        read_only_fields = [
            "id", "organization", "organization_slug", "raw_token", "accepted_at",
            "revoked_at", "created_at",
        ]

    def create(self, validated_data):
        request = self.context["request"]
        organization = self.context["organization"]
        raw_token = generate_invitation_token()
        invitation = OrganizationInvitation.objects.create(
            organization=organization,
            invited_by=request.user,
            token_hash=hash_invitation_token(raw_token),
            **validated_data,
        )
        invitation.raw_token = raw_token
        write_audit_event(
            request=request,
            actor=request.user,
            category=AuditLog.Category.ADMIN,
            action="organization.invitation.created",
            subject_user_id=None,
            metadata={
                "organization_id": str(organization.id),
                "email": invitation.email,
                "role": invitation.role,
            },
        )
        return invitation


class OrganizationInvitationAcceptSerializer(serializers.Serializer):
    token = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_token(self, value):
        invitation = find_active_invitation(value)
        if not invitation:
            raise serializers.ValidationError("Invalid or expired invitation token.")
        self.invitation = invitation
        return value

    def save(self, **kwargs):
        request = self.context["request"]
        invitation = self.invitation
        if request.user.email.lower() != invitation.email.lower():
            raise serializers.ValidationError({"email": "This invitation was issued for a different email address."})
        membership, _ = OrganizationMembership.objects.update_or_create(
            organization=invitation.organization,
            user=request.user,
            defaults={
                "role": invitation.role,
                "is_active": True,
                "invited_by": invitation.invited_by,
                "joined_at": timezone.now(),
            },
        )
        invitation.mark_accepted()
        write_audit_event(
            request=request,
            actor=request.user,
            category=AuditLog.Category.ADMIN,
            action="organization.invitation.accepted",
            metadata={"organization_id": str(invitation.organization_id), "membership_id": str(membership.id)},
        )
        return membership


class TenantServiceCredentialSerializer(serializers.ModelSerializer):
    raw_key = serializers.CharField(read_only=True)
    organization_slug = serializers.CharField(source="organization.slug", read_only=True)

    class Meta:
        model = TenantServiceCredential
        fields = [
            "id", "organization", "organization_slug", "name", "key_prefix", "raw_key",
            "scopes", "is_active", "last_used_at", "expires_at", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "organization", "organization_slug", "key_prefix", "raw_key",
            "is_active", "last_used_at", "created_at", "updated_at",
        ]

    def validate_scopes(self, value):
        try:
            return validate_tenant_service_scopes(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc

    def create(self, validated_data):
        request = self.context["request"]
        organization = self.context["organization"]
        raw_key = generate_tenant_service_key()
        credential = TenantServiceCredential.objects.create(
            organization=organization,
            created_by=request.user,
            key_prefix=tenant_service_key_prefix(raw_key),
            key_hash=hash_tenant_service_key(raw_key),
            **validated_data,
        )
        credential.raw_key = raw_key
        write_audit_event(
            request=request,
            actor=request.user,
            category=AuditLog.Category.SERVICE,
            action="tenant_service_credential.created",
            metadata={"organization_id": str(organization.id), "credential_id": str(credential.id)},
        )
        return credential


class TenantServiceCredentialRotateSerializer(serializers.Serializer):
    raw_key = serializers.CharField(read_only=True)
    key_prefix = serializers.CharField(read_only=True)

    def save(self, **kwargs):
        credential = self.context["credential"]
        request = self.context["request"]
        raw_key = generate_tenant_service_key()
        credential.key_prefix = tenant_service_key_prefix(raw_key)
        credential.key_hash = hash_tenant_service_key(raw_key)
        credential.last_used_at = None
        credential.save(update_fields=["key_prefix", "key_hash", "last_used_at", "updated_at"])
        write_audit_event(
            request=request,
            actor=request.user,
            category=AuditLog.Category.SERVICE,
            action="tenant_service_credential.rotated",
            metadata={"organization_id": str(credential.organization_id), "credential_id": str(credential.id)},
        )
        return {"raw_key": raw_key, "key_prefix": credential.key_prefix}

# Imported at module end to keep v8 append-only changes easy to review.
from .audit import write_audit_event

from .authorization import (
    get_role_permissions,
    get_user_permissions,
    list_permission_catalog,
    normalize_permission_code,
    service_has_permission,
    user_has_permission,
)


class PermissionCatalogSerializer(serializers.Serializer):
    code = serializers.CharField()


class PermissionPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = PermissionPolicy
        fields = [
            "id", "organization", "code", "name", "description", "is_active",
            "metadata", "expires_at", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "organization", "created_at", "updated_at"]

    def validate_code(self, value):
        return normalize_permission_code(value)

    def create(self, validated_data):
        request = self.context["request"]
        organization = self.context["organization"]
        policy = PermissionPolicy.objects.create(
            organization=organization,
            created_by=request.user,
            **validated_data,
        )
        write_audit_event(
            request=request,
            actor=request.user,
            category=AuditLog.Category.ADMIN,
            action="permission_policy.created",
            metadata={"organization_id": str(organization.id), "policy_id": str(policy.id), "code": policy.code},
        )
        return policy


class RolePermissionGrantSerializer(serializers.ModelSerializer):
    policy_code = serializers.CharField(source="policy.code", read_only=True)

    class Meta:
        model = RolePermissionGrant
        fields = [
            "id", "organization", "role", "policy", "policy_code", "effect",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "organization", "policy_code", "created_at", "updated_at"]

    def validate_policy(self, value):
        organization = self.context["organization"]
        if value.organization_id != organization.id:
            raise serializers.ValidationError("Policy must belong to the same organization.")
        return value

    def create(self, validated_data):
        request = self.context["request"]
        organization = self.context["organization"]
        grant, _ = RolePermissionGrant.objects.update_or_create(
            organization=organization,
            role=validated_data["role"],
            policy=validated_data["policy"],
            defaults={"effect": validated_data.get("effect", RolePermissionGrant.Effect.ALLOW), "created_by": request.user},
        )
        write_audit_event(
            request=request,
            actor=request.user,
            category=AuditLog.Category.ADMIN,
            action="role_permission_grant.upserted",
            metadata={
                "organization_id": str(organization.id),
                "grant_id": str(grant.id),
                "role": grant.role,
                "policy": grant.policy.code,
                "effect": grant.effect,
            },
        )
        return grant


class RolePermissionMatrixSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=OrganizationMembership.Role.choices)
    permissions = serializers.ListField(child=serializers.CharField(), read_only=True)

    def to_representation(self, instance):
        organization = self.context["organization"]
        role = instance if isinstance(instance, str) else instance.get("role")
        return {"role": role, "permissions": sorted(get_role_permissions(organization, role))}


class AccessCheckSerializer(serializers.Serializer):
    permission = serializers.CharField()
    user_id = serializers.UUIDField(required=False)
    service_credential_id = serializers.UUIDField(required=False)
    allowed = serializers.BooleanField(read_only=True)
    principal_type = serializers.CharField(read_only=True)
    principal_id = serializers.CharField(read_only=True)

    def validate_permission(self, value):
        return normalize_permission_code(value)

    def validate(self, attrs):
        if attrs.get("user_id") and attrs.get("service_credential_id"):
            raise serializers.ValidationError("Check either a user or a service credential, not both.")
        return attrs

    def save(self, **kwargs):
        request = self.context["request"]
        organization = self.context["organization"]
        permission = self.validated_data["permission"]
        if self.validated_data.get("service_credential_id"):
            credential = TenantServiceCredential.objects.filter(
                id=self.validated_data["service_credential_id"],
                organization=organization,
                is_active=True,
            ).first()
            allowed = bool(credential and service_has_permission(credential, permission))
            principal_type = "tenant_service_credential"
            principal_id = str(credential.id) if credential else str(self.validated_data["service_credential_id"])
        else:
            user = request.user
            if self.validated_data.get("user_id"):
                user = User.objects.filter(id=self.validated_data["user_id"], is_active=True).first()
            allowed = bool(user and user_has_permission(user, organization, permission))
            principal_type = "user"
            principal_id = str(user.id) if user else str(self.validated_data.get("user_id", ""))
        return {
            "permission": permission,
            "allowed": allowed,
            "principal_type": principal_type,
            "principal_id": principal_id,
        }


class UserPermissionSummarySerializer(serializers.Serializer):
    permissions = serializers.ListField(child=serializers.CharField(), read_only=True)

    def save(self, **kwargs):
        request = self.context["request"]
        organization = self.context["organization"]
        return {"permissions": sorted(get_user_permissions(request.user, organization))}

