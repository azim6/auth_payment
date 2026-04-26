import pytest

from fraud_abuse.models import AbuseSignal, IPReputation, VelocityRule
from fraud_abuse.services import evaluate_velocity_rules, record_velocity_event, register_abuse_signal, score_to_severity, upsert_ip_reputation


@pytest.mark.django_db
def test_score_to_severity_mapping():
    assert score_to_severity(5) == AbuseSignal.Severity.INFO
    assert score_to_severity(35) == AbuseSignal.Severity.LOW
    assert score_to_severity(55) == AbuseSignal.Severity.MEDIUM
    assert score_to_severity(80) == AbuseSignal.Severity.HIGH
    assert score_to_severity(95) == AbuseSignal.Severity.CRITICAL


@pytest.mark.django_db
def test_abuse_signal_idempotency():
    first = register_abuse_signal(category=AbuseSignal.Category.AUTH, signal="auth.login_failed", score=45, summary="Failed login", idempotency_key="evt-1")
    second = register_abuse_signal(category=AbuseSignal.Category.AUTH, signal="auth.login_failed", score=45, summary="Failed login", idempotency_key="evt-1")
    assert first.id == second.id
    assert AbuseSignal.objects.count() == 1


@pytest.mark.django_db
def test_velocity_rule_match_creates_signal():
    VelocityRule.objects.create(name="Many failed logins per IP", event_name="auth.login_failed", scope="ip", threshold=2, window_seconds=300, risk_score=75)
    record_velocity_event(event_name="auth.login_failed", ip_address="203.0.113.10")
    event = record_velocity_event(event_name="auth.login_failed", ip_address="203.0.113.10")
    matches = evaluate_velocity_rules(event)
    assert len(matches) == 1
    assert matches[0]["signal"].score == 75


@pytest.mark.django_db
def test_ip_reputation_upsert_keeps_highest_score():
    upsert_ip_reputation(ip_address="203.0.113.20", reputation=IPReputation.Reputation.SUSPICIOUS, risk_score=30)
    record = upsert_ip_reputation(ip_address="203.0.113.20", reputation=IPReputation.Reputation.UNKNOWN, risk_score=80)
    assert record.risk_score == 80
    assert record.reputation == IPReputation.Reputation.SUSPICIOUS
