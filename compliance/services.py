from accounts.audit import write_audit_event


def log_compliance_event(request, action, metadata=None):
    """Write compliance governance actions into the central append-only audit log."""
    actor = getattr(request, "user", None)
    if actor is not None and not getattr(actor, "is_authenticated", False):
        actor = None
    return write_audit_event(
        request=request,
        actor=actor,
        category="admin",
        action=action,
        outcome="success",
        metadata=metadata or {},
    )
