import pytest
from django.utils import timezone

from accounts.models import Organization
from billing.models import BillingProfile, BillingCustomer, CreditNote, CustomerTaxId, DunningCase, PaymentTransaction, RefundRequest
from billing.services import get_or_create_billing_profile, issue_credit_note, review_refund_request, open_or_update_dunning_case


@pytest.mark.django_db
def test_billing_profile_and_tax_id_are_customer_scoped(user):
    org = Organization.objects.create(name="Acme", slug="acme", owner=user)
    customer = BillingCustomer.objects.create(organization=org, billing_email="billing@example.com", billing_name="Acme Ltd")

    profile = get_or_create_billing_profile(customer)
    profile.legal_name = "Acme Ltd"
    profile.country = "US"
    profile.save()

    tax_id = CustomerTaxId.objects.create(customer=customer, tax_type="us_ein", value="12-3456789", country="US")

    assert profile.customer == customer
    assert tax_id.customer == customer
    assert tax_id.status == CustomerTaxId.Status.PENDING


@pytest.mark.django_db
def test_issue_credit_note_allocates_number_and_audit(admin_user):
    org = Organization.objects.create(name="Acme", slug="acme", owner=admin_user)
    customer = BillingCustomer.objects.create(organization=org, billing_email="billing@example.com", billing_name="Acme Ltd")
    BillingProfile.objects.create(customer=customer, invoice_prefix="ACME")

    credit = issue_credit_note(customer=customer, amount_cents=2500, currency="USD", actor=admin_user, memo="Service credit")

    assert credit.number == "ACME-000001"
    assert credit.status == CreditNote.Status.ISSUED
    assert credit.issued_by == admin_user


@pytest.mark.django_db
def test_refund_review_marks_processed_and_payment_refunded(admin_user):
    org = Organization.objects.create(name="Acme", slug="acme", owner=admin_user)
    customer = BillingCustomer.objects.create(organization=org, billing_email="billing@example.com", billing_name="Acme Ltd")
    payment = PaymentTransaction.objects.create(customer=customer, status=PaymentTransaction.Status.SUCCEEDED, amount_cents=5000)
    refund = RefundRequest.objects.create(customer=customer, payment=payment, amount_cents=5000, requested_by=admin_user)

    refund = review_refund_request(refund=refund, actor=admin_user, action="process", provider_refund_id="re_123")
    payment.refresh_from_db()

    assert refund.status == RefundRequest.Status.PROCESSED
    assert payment.status == PaymentTransaction.Status.REFUNDED


@pytest.mark.django_db
def test_dunning_case_tracks_failures(admin_user):
    org = Organization.objects.create(name="Acme", slug="acme", owner=admin_user)
    customer = BillingCustomer.objects.create(organization=org, billing_email="billing@example.com", billing_name="Acme Ltd")

    case = open_or_update_dunning_case(customer=customer, failure_time=timezone.now())
    case = open_or_update_dunning_case(customer=customer, failure_time=timezone.now())

    assert case.failed_attempts == 2
    assert case.status == DunningCase.Status.OPEN
