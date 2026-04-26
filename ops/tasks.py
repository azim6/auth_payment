from config.celery import app

from .services import persist_environment_checks, run_health_checks


@app.task
def refresh_operations_state():
    """Periodic task for deployment readiness dashboards and alerting."""
    persist_environment_checks()
    run_health_checks()
    return {"ok": True}
