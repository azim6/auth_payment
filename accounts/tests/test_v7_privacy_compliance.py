import pytest
from django.urls import reverse
from django.utils import timezone

from accounts.models import AccountDeletionRequest, DataExportRequest, PrivacyPreference, UserConsent


@pytest.mark.django_db
def test_privacy_preferences_can_be_updated(api_client, user):
    api_client.force_authenticate(user=user)
    response = api_client.patch(reverse("privacy-preferences"), {"analytics_consent": True}, format="json")
    assert response.status_code == 200
    assert PrivacyPreference.objects.get(user=user).analytics_consent is True


@pytest.mark.django_db
def test_consent_is_append_only(api_client, user):
    api_client.force_authenticate(user=user)
    payload = {"consent_type": "privacy", "version": "privacy-2026-04-24", "granted": True, "source": "web"}
    response = api_client.post(reverse("privacy-consents"), payload, format="json")
    assert response.status_code == 201
    assert UserConsent.objects.filter(user=user, consent_type="privacy", version="privacy-2026-04-24").exists()


@pytest.mark.django_db
def test_data_export_request_is_created(api_client, user):
    api_client.force_authenticate(user=user)
    response = api_client.post(reverse("privacy-data-exports"), {}, format="json")
    assert response.status_code == 202
    assert DataExportRequest.objects.filter(user=user).exists()


@pytest.mark.django_db
def test_data_export_payload_contains_user_and_consents(api_client, user):
    api_client.force_authenticate(user=user)
    UserConsent.objects.create(user=user, consent_type="terms", version="terms-1", granted=True, source="web")
    response = api_client.get(reverse("privacy-data-export-payload"))
    assert response.status_code == 200
    assert response.data["user"]["email"] == user.email
    assert response.data["consents"][0]["version"] == "terms-1"


@pytest.mark.django_db
def test_account_deletion_request_confirm_and_cancel(api_client, user):
    api_client.force_authenticate(user=user)
    created = api_client.post(reverse("privacy-account-deletion"), {"reason": "no longer needed"}, format="json")
    assert created.status_code == 202
    deletion_id = created.data["id"]
    confirm = api_client.post(reverse("privacy-account-deletion-confirm"), {"deletion_request_id": deletion_id}, format="json")
    assert confirm.status_code == 200
    deletion = AccountDeletionRequest.objects.get(id=deletion_id)
    assert deletion.status == AccountDeletionRequest.Status.CONFIRMED
    user.refresh_from_db()
    assert user.is_active is False
    cancel = api_client.post(reverse("privacy-account-deletion-cancel"), {"deletion_request_id": deletion_id}, format="json")
    assert cancel.status_code == 200
    user.refresh_from_db()
    assert user.is_active is True
