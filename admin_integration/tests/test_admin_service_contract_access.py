import json

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import Organization
from admin_integration.services import body_sha256, create_admin_service_credential, sign_request
from billing.models import BillingCustomer, EntitlementChangeLog
from security_ops.models import AccountRestriction


pytestmark = pytest.mark.django_db


def _signed_headers(*, credential_key, signing_secret, method, path, body=b"", nonce="nonce-1", timestamp="1760000000"):
    body_hash = body_sha256(body)
    signature = sign_request(signing_secret, method, path, timestamp, nonce, body_hash)
    return {
        "HTTP_X_ADMIN_SERVICE_KEY": credential_key,
        "HTTP_X_ADMIN_TIMESTAMP": timestamp,
        "HTTP_X_ADMIN_NONCE": nonce,
        "HTTP_X_ADMIN_SIGNATURE": signature,
    }


def test_admin_service_can_read_contract_endpoints():
    User = get_user_model()
    staff = User.objects.create_user(
        email="staff@example.com",
        username="staff",
        password="CorrectHorseBatteryStaple123!",
        is_staff=True,
    )
    target_user = User.objects.create_user(
        email="member@example.com",
        username="member",
        password="CorrectHorseBatteryStaple123!",
    )
    org = Organization.objects.create(name="Acme", slug="acme")
    credential, api_key, signing_secret = create_admin_service_credential(
        name="admin-platform",
        scopes="admin:readiness admin:read",
        created_by=staff,
    )
    assert credential.scope_set == {"admin:readiness", "admin:read"}

    client = APIClient()
    readiness_path = reverse("auth-readiness")
    readiness_response = client.get(
        readiness_path,
        **_signed_headers(credential_key=api_key, signing_secret=signing_secret, method="GET", path=readiness_path),
    )
    assert readiness_response.status_code == 200

    contract_path = reverse("admin-api-contract")
    contract_response = client.get(
        contract_path,
        **_signed_headers(credential_key=api_key, signing_secret=signing_secret, method="GET", path=contract_path, nonce="nonce-2"),
    )
    assert contract_response.status_code == 200
    assert any(item["path"] == "/api/v1/admin-console/users/{user_id}/overview/" for item in contract_response.json())

    user_overview_path = reverse("admin-console-user-overview", kwargs={"user_id": target_user.id})
    user_response = client.get(
        user_overview_path,
        **_signed_headers(credential_key=api_key, signing_secret=signing_secret, method="GET", path=user_overview_path, nonce="nonce-3"),
    )
    assert user_response.status_code == 200
    assert user_response.json()["user"]["email"] == target_user.email

    org_overview_path = reverse("admin-console-org-overview", kwargs={"slug": org.slug})
    org_response = client.get(
        org_overview_path,
        **_signed_headers(credential_key=api_key, signing_secret=signing_secret, method="GET", path=org_overview_path, nonce="nonce-4"),
    )
    assert org_response.status_code == 200
    assert org_response.json()["organization"]["slug"] == org.slug


def test_admin_service_scope_is_enforced_for_sensitive_contract_endpoints():
    User = get_user_model()
    staff = User.objects.create_user(
        email="staff@example.com",
        username="staff",
        password="CorrectHorseBatteryStaple123!",
        is_staff=True,
    )
    org = Organization.objects.create(name="Acme", slug="acme")
    customer = BillingCustomer.objects.create(organization=org, billing_email="billing@example.com")
    _, api_key, signing_secret = create_admin_service_credential(
        name="read-only-admin-platform",
        scopes="admin:readiness admin:read",
        created_by=staff,
    )

    client = APIClient()
    payload = json.dumps({"customer": str(customer.id), "reason": "admin-check"}, separators=(",", ":")).encode("utf-8")
    recalc_path = reverse("billing-recalculate-entitlement-snapshot-with-log")
    recalc_response = client.post(
        recalc_path,
        data=payload,
        content_type="application/json",
        **_signed_headers(credential_key=api_key, signing_secret=signing_secret, method="POST", path=recalc_path, body=payload),
    )
    assert recalc_response.status_code == 403


def test_admin_service_can_trigger_security_and_entitlement_actions():
    User = get_user_model()
    staff = User.objects.create_user(
        email="staff@example.com",
        username="staff",
        password="CorrectHorseBatteryStaple123!",
        is_staff=True,
    )
    target_user = User.objects.create_user(
        email="member@example.com",
        username="member",
        password="CorrectHorseBatteryStaple123!",
    )
    org = Organization.objects.create(name="Acme", slug="acme")
    customer = BillingCustomer.objects.create(organization=org, billing_email="billing@example.com")
    _, api_key, signing_secret = create_admin_service_credential(
        name="writer-admin-platform",
        scopes="admin:readiness admin:read admin:security:write admin:entitlements:write",
        created_by=staff,
    )
    client = APIClient()

    restriction_payload = json.dumps(
        {"user": str(target_user.id), "organization": str(org.id), "restriction_type": "api_block", "reason": "admin-freeze"},
        separators=(",", ":"),
    ).encode("utf-8")
    restriction_path = reverse("security-account-restrictions")
    restriction_response = client.post(
        restriction_path,
        data=restriction_payload,
        content_type="application/json",
        **_signed_headers(credential_key=api_key, signing_secret=signing_secret, method="POST", path=restriction_path, body=restriction_payload, nonce="nonce-5"),
    )
    assert restriction_response.status_code == 201
    restriction = AccountRestriction.objects.get(id=restriction_response.json()["id"])
    assert restriction.created_by is None
    assert restriction.metadata["admin_service_credential_name"] == "writer-admin-platform"

    recalc_payload = json.dumps({"customer": str(customer.id), "reason": "admin-sync"}, separators=(",", ":")).encode("utf-8")
    recalc_path = reverse("billing-recalculate-entitlement-snapshot-with-log")
    recalc_response = client.post(
        recalc_path,
        data=recalc_payload,
        content_type="application/json",
        **_signed_headers(credential_key=api_key, signing_secret=signing_secret, method="POST", path=recalc_path, body=recalc_payload, nonce="nonce-6"),
    )
    assert recalc_response.status_code == 200
    log = EntitlementChangeLog.objects.get(customer=customer)
    assert log.changed_by is None
    assert log.metadata["admin_service_credential_name"] == "writer-admin-platform"
