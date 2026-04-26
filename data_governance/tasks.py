from __future__ import annotations

from celery import shared_task

from .models import RetentionJob, RetentionPolicy
from .services import create_inventory_snapshot, plan_retention_job, run_retention_job


@shared_task
def generate_data_inventory_snapshot() -> str:
    snapshot = create_inventory_snapshot(user=None)
    return str(snapshot.id)


@shared_task
def plan_active_retention_jobs(dry_run: bool = True) -> int:
    count = 0
    for policy in RetentionPolicy.objects.filter(is_active=True):
        plan_retention_job(policy, user=None, dry_run=dry_run)
        count += 1
    return count


@shared_task
def run_due_retention_jobs() -> int:
    count = 0
    for job in RetentionJob.objects.filter(status=RetentionJob.Status.QUEUED):
        run_retention_job(job)
        count += 1
    return count
