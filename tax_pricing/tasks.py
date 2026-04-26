from celery import shared_task


@shared_task
def refresh_tax_pricing_snapshot():
    """Placeholder task for future provider-driven FX/tax refresh jobs."""
    return {"status": "ok", "message": "tax/pricing snapshot refresh placeholder"}
