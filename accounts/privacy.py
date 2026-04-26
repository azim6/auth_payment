from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .audit import write_audit_event
from .models import (
    AccountDeletionRequest,
    DataExportRequest,
    PrivacyPreference,
    User,
    UserConsent,
)


def client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def user_agent(request):
    return request.META.get("HTTP_USER_AGENT", "")[:4000]


def get_or_create_privacy_preferences(user: User) -> PrivacyPreference:
    preferences, _ = PrivacyPreference.objects.get_or_create(user=user)
    return preferences


def record_consent(*, user: User, consent_type: str, version: str, granted: bool, source: str, request=None, metadata=None) -> UserConsent:
    consent = UserConsent.objects.create(
        user=user,
        consent_type=consent_type,
        version=version,
        granted=granted,
        source=source,
        ip_address=client_ip(request) if request else None,
        user_agent=user_agent(request) if request else "",
        metadata=metadata or {},
    )
    if consent_type == UserConsent.ConsentType.TERMS and granted:
        User.objects.filter(pk=user.pk).update(terms_accepted_at=timezone.now())
    if consent_type == UserConsent.ConsentType.PRIVACY and granted:
        User.objects.filter(pk=user.pk).update(privacy_policy_accepted_at=timezone.now())
    return consent


def build_user_export_payload(user: User) -> dict:
    preferences = get_or_create_privacy_preferences(user)
    return {
        "schema_version": "2026-04-v1",
        "generated_at": timezone.now().isoformat(),
        "user": {
            "id": str(user.id),
            "email": user.email,
            "username": user.username,
            "display_name": user.display_name,
            "avatar_url": user.avatar_url,
            "bio": user.bio,
            "email_verified": user.email_verified,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None,
        },
        "privacy_preferences": {
            "analytics_consent": preferences.analytics_consent,
            "marketing_email_consent": preferences.marketing_email_consent,
            "product_email_consent": preferences.product_email_consent,
            "profile_discoverable": preferences.profile_discoverable,
            "data_processing_region": preferences.data_processing_region,
            "updated_at": preferences.updated_at.isoformat() if preferences.updated_at else None,
        },
        "consents": [
            {
                "consent_type": consent.consent_type,
                "version": consent.version,
                "granted": consent.granted,
                "source": consent.source,
                "created_at": consent.created_at.isoformat() if consent.created_at else None,
            }
            for consent in user.consents.order_by("-created_at")[:500]
        ],
    }


def create_data_export_request(*, user: User, request=None) -> DataExportRequest:
    export = DataExportRequest.objects.create(
        user=user,
        requested_ip=client_ip(request) if request else None,
        requested_user_agent=user_agent(request) if request else "",
    )
    write_audit_event(
        actor=user,
        category="account",
        action="data_export_requested",
        request=request,
        subject_user_id=user.id,
        metadata={"export_request_id": str(export.id)},
    )
    return export


@transaction.atomic
def mark_data_export_ready(*, export: DataExportRequest, download_url: str = "") -> DataExportRequest:
    export.status = DataExportRequest.Status.READY
    export.download_url = download_url
    export.completed_at = timezone.now()
    export.expires_at = timezone.now() + timedelta(days=getattr(settings, "DATA_EXPORT_EXPIRY_DAYS", 7))
    export.save(update_fields=["status", "download_url", "completed_at", "expires_at", "updated_at"])
    return export


def create_account_deletion_request(*, user: User, reason: str = "", request=None) -> AccountDeletionRequest:
    now = timezone.now()
    deletion = AccountDeletionRequest.objects.create(
        user=user,
        reason=reason,
        requested_ip=client_ip(request) if request else None,
        requested_user_agent=user_agent(request) if request else "",
        confirm_before=now + timedelta(hours=getattr(settings, "ACCOUNT_DELETION_CONFIRM_WINDOW_HOURS", 24)),
        scheduled_for=now + timedelta(days=getattr(settings, "ACCOUNT_DELETION_GRACE_DAYS", 30)),
    )
    write_audit_event(
        actor=user,
        category="account",
        action="account_deletion_requested",
        request=request,
        subject_user_id=user.id,
        metadata={"deletion_request_id": str(deletion.id)},
    )
    return deletion


@transaction.atomic
def confirm_account_deletion(*, deletion: AccountDeletionRequest, request=None) -> AccountDeletionRequest:
    if not deletion.is_confirmable:
        raise ValueError("Deletion request is not confirmable.")
    deletion.status = AccountDeletionRequest.Status.CONFIRMED
    deletion.confirmed_at = timezone.now()
    deletion.save(update_fields=["status", "confirmed_at", "updated_at"])
    User.objects.filter(pk=deletion.user_id).update(is_active=False)
    write_audit_event(
        actor=deletion.user,
        category="account",
        action="account_deletion_confirmed",
        request=request,
        subject_user_id=deletion.user_id,
        metadata={"deletion_request_id": str(deletion.id), "scheduled_for": deletion.scheduled_for.isoformat()},
    )
    return deletion


@transaction.atomic
def cancel_account_deletion(*, deletion: AccountDeletionRequest, request=None) -> AccountDeletionRequest:
    if deletion.status not in {AccountDeletionRequest.Status.PENDING, AccountDeletionRequest.Status.CONFIRMED}:
        raise ValueError("Deletion request cannot be cancelled.")
    deletion.status = AccountDeletionRequest.Status.CANCELLED
    deletion.cancelled_at = timezone.now()
    deletion.save(update_fields=["status", "cancelled_at", "updated_at"])
    User.objects.filter(pk=deletion.user_id).update(is_active=True)
    write_audit_event(
        actor=deletion.user,
        category="account",
        action="account_deletion_cancelled",
        request=request,
        subject_user_id=deletion.user_id,
        metadata={"deletion_request_id": str(deletion.id)},
    )
    return deletion
