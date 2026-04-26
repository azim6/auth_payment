import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from compliance.models import AdminApprovalRequest, AuditExport, EvidencePack, PolicyDocument, UserPolicyAcceptance


def make_admin_client(email="admin@example.com"):
    admin = User.objects.create_superuser(email=email, username=email.split("@")[0], password="AdminPass123!")
    client = APIClient()
    client.force_authenticate(user=admin)
    return client, admin


def make_user(email="user@example.com"):
    return User.objects.create_user(email=email, username=email.split("@")[0], password="UserPass123!")


@pytest.mark.django_db
def test_staff_can_create_and_publish_policy():
    admin_client, _ = make_admin_client()
    response = admin_client.post(
        reverse("compliance-policies"),
        {
            "policy_type": PolicyDocument.PolicyType.TERMS,
            "version": "2026.04",
            "title": "Terms of Service 2026.04",
            "body": "Initial production terms.",
            "requires_user_acceptance": True,
        },
        format="json",
    )
    assert response.status_code == 201
    policy_id = response.data["id"]

    publish = admin_client.post(reverse("compliance-policy-publish", args=[policy_id]), {}, format="json")
    assert publish.status_code == 200
    assert publish.data["is_active"] is True
    assert publish.data["published_at"] is not None


@pytest.mark.django_db
def test_user_can_accept_active_policy():
    user = make_user()
    client = APIClient()
    client.force_authenticate(user=user)
    policy = PolicyDocument.objects.create(
        policy_type=PolicyDocument.PolicyType.PRIVACY,
        version="2026.04",
        title="Privacy Policy",
        is_active=True,
        published_at=timezone.now(),
    )

    response = client.post(reverse("compliance-policy-acceptances"), {"policy": str(policy.id)}, format="json")
    assert response.status_code == 201
    assert UserPolicyAcceptance.objects.filter(user=user, policy=policy).exists()


@pytest.mark.django_db
def test_requester_cannot_approve_own_admin_approval():
    client, admin = make_admin_client()
    approval = AdminApprovalRequest.objects.create(
        requested_by=admin,
        action_type=AdminApprovalRequest.ActionType.BILLING_OVERRIDE,
        summary="Give customer custom annual price",
        reason="Sales approved custom contract.",
    )

    response = client.post(
        reverse("compliance-approval-review", args=[approval.id]),
        {"action": "approve", "notes": "self approve"},
        format="json",
    )
    assert response.status_code >= 400
    approval.refresh_from_db()
    assert approval.status == AdminApprovalRequest.Status.PENDING


@pytest.mark.django_db
def test_staff_can_mark_audit_export_ready():
    admin_client, admin = make_admin_client()
    export = AuditExport.objects.create(
        requested_by=admin,
        export_type=AuditExport.ExportType.FULL_EVIDENCE,
    )
    response = admin_client.post(
        reverse("compliance-audit-export-ready", args=[export.id]),
        {
            "storage_uri": "s3://private-audit-exports/example.jsonl.gz",
            "checksum_sha256": "a" * 64,
            "record_count": 42,
        },
        format="json",
    )
    assert response.status_code == 200
    assert response.data["status"] == AuditExport.Status.READY
    assert response.data["record_count"] == 42


@pytest.mark.django_db
def test_staff_can_lock_evidence_pack():
    admin_client, admin = make_admin_client()
    pack = EvidencePack.objects.create(
        created_by=admin,
        pack_type=EvidencePack.PackType.COMPLIANCE_REVIEW,
        title="Quarterly compliance review",
    )
    response = admin_client.post(reverse("compliance-evidence-pack-lock", args=[pack.id]), {}, format="json")
    assert response.status_code == 200
    assert response.data["status"] == EvidencePack.Status.LOCKED
    assert response.data["locked_at"] is not None
