from __future__ import annotations

import hashlib
from django.utils import timezone

from .models import (
    AnonymizationRecord,
    DataAsset,
    DataCategory,
    DataInventorySnapshot,
    DataSubjectRequest,
    LegalHold,
    RetentionJob,
    RetentionPolicy,
)


def hash_subject_id(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def create_inventory_snapshot(user=None, include_assets: bool = True) -> DataInventorySnapshot:
    assets = DataAsset.objects.all()
    summary = {}
    if include_assets:
        summary["assets"] = [
            {
                "key": asset.key,
                "app_label": asset.app_label,
                "model_name": asset.model_name,
                "contains_pii": asset.contains_pii,
                "contains_payment_data": asset.contains_payment_data,
                "sensitivity": [category.sensitivity for category in asset.categories.all()],
            }
            for asset in assets.prefetch_related("categories")[:500]
        ]
    return DataInventorySnapshot.objects.create(
        generated_by=user if getattr(user, "is_authenticated", False) else None,
        asset_count=assets.count(),
        pii_asset_count=assets.filter(contains_pii=True).count(),
        restricted_asset_count=assets.filter(categories__sensitivity="restricted").distinct().count(),
        active_policy_count=RetentionPolicy.objects.filter(is_active=True).count(),
        active_legal_hold_count=LegalHold.objects.filter(status=LegalHold.Status.ACTIVE).count(),
        open_subject_request_count=DataSubjectRequest.objects.exclude(status__in=[DataSubjectRequest.Status.COMPLETED, DataSubjectRequest.Status.REJECTED]).count(),
        summary=summary,
    )


def has_active_hold(user=None, organization=None, category: DataCategory | None = None) -> bool:
    now = timezone.now()
    holds = LegalHold.objects.filter(status=LegalHold.Status.ACTIVE, starts_at__lte=now).filter(models_current(now))
    if holds.filter(scope=LegalHold.Scope.GLOBAL).exists():
        return True
    if user and holds.filter(scope=LegalHold.Scope.USER, user=user).exists():
        return True
    if organization and holds.filter(scope=LegalHold.Scope.ORGANIZATION, organization=organization).exists():
        return True
    if category and holds.filter(scope=LegalHold.Scope.CATEGORY, category=category).exists():
        return True
    return False


def models_current(now):
    from django.db.models import Q
    return Q(ends_at__isnull=True) | Q(ends_at__gt=now)


def release_legal_hold(hold: LegalHold, user) -> LegalHold:
    hold.status = LegalHold.Status.RELEASED
    hold.released_at = timezone.now()
    hold.released_by = user
    hold.save(update_fields=["status", "released_at", "released_by"])
    return hold


def plan_retention_job(policy: RetentionPolicy, user=None, dry_run: bool = True) -> RetentionJob:
    cutoff_at = timezone.now() - timezone.timedelta(days=policy.retention_days + policy.grace_days)
    # v22 keeps execution provider-neutral. Candidate counts are conservative metadata from governed assets,
    # not direct table mutations. Future versions can register per-app retention handlers.
    candidate_count = policy.assets.count()
    blocked_count = LegalHold.objects.filter(status=LegalHold.Status.ACTIVE).count() if policy.legal_hold_exempt else 0
    job = RetentionJob.objects.create(
        policy=policy,
        dry_run=dry_run,
        cutoff_at=cutoff_at,
        candidate_count=candidate_count,
        blocked_count=blocked_count,
        created_by=user if getattr(user, "is_authenticated", False) else None,
        result_summary={"mode": "plan", "policy": policy.key, "candidate_assets": candidate_count},
    )
    return job


def run_retention_job(job: RetentionJob, force: bool = False) -> RetentionJob:
    if job.status == RetentionJob.Status.COMPLETED and not force:
        return job
    job.status = RetentionJob.Status.RUNNING
    job.started_at = timezone.now()
    job.save(update_fields=["status", "started_at"])
    if job.blocked_count and job.policy.legal_hold_exempt and not force:
        job.status = RetentionJob.Status.BLOCKED
        job.result_summary = {**job.result_summary, "blocked_reason": "active_legal_hold"}
        job.completed_at = timezone.now()
        job.save(update_fields=["status", "result_summary", "completed_at"])
        return job
    processed = 0
    for asset in job.policy.assets.all():
        AnonymizationRecord.objects.create(
            job=job,
            asset=asset,
            subject_type="asset",
            subject_id_hash=hash_subject_id(str(asset.id)),
            action=job.policy.action,
            fields_changed=[],
            metadata={"dry_run": job.dry_run, "asset_key": asset.key},
        )
        processed += 1
    job.processed_count = processed
    job.status = RetentionJob.Status.COMPLETED
    job.completed_at = timezone.now()
    job.result_summary = {**job.result_summary, "processed_assets": processed, "dry_run": job.dry_run}
    job.save(update_fields=["processed_count", "status", "completed_at", "result_summary"])
    return job


def governance_summary() -> dict:
    return {
        "categories": DataCategory.objects.count(),
        "assets": DataAsset.objects.count(),
        "pii_assets": DataAsset.objects.filter(contains_pii=True).count(),
        "payment_assets": DataAsset.objects.filter(contains_payment_data=True).count(),
        "active_retention_policies": RetentionPolicy.objects.filter(is_active=True).count(),
        "active_legal_holds": LegalHold.objects.filter(status=LegalHold.Status.ACTIVE).count(),
        "open_subject_requests": DataSubjectRequest.objects.exclude(status__in=[DataSubjectRequest.Status.COMPLETED, DataSubjectRequest.Status.REJECTED]).count(),
        "queued_retention_jobs": RetentionJob.objects.filter(status=RetentionJob.Status.QUEUED).count(),
    }
