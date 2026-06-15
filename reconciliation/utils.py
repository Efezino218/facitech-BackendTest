from django.utils import timezone
from django.db.models import Sum
from bills.models import Bill, ExternalPayment
from .models import ReconciliationRecord, PeriodSummary


def reconcile_bill(bill):
    """
    Creates or updates a reconciliation record for a single bill.
    Determines match status based on bill and payment data.

    Match rules:
    - MATCH: bill is verified and amounts match
    - UNVERIFIED: bill is paid but not yet verified by ISCOOA
    - GAP: bill is unpaid or there is a variance
    """
    # Determine operator payment amount and method
    operator_amount = 0
    operator_method = ''
    paid_ref        = ''
    external_payment_obj = None

    if bill.status == 'verified':
        # Paid via Cool MFB wallet
        operator_amount = bill.total
        operator_method = 'Cool MFB Wallet'
        paid_ref        = bill.paid_ref

    elif bill.status == 'paid':
        # Paid but not yet verified
        operator_amount = bill.total
        operator_method = 'Cool MFB Wallet'
        paid_ref        = bill.paid_ref

    else:
        # Check for external payments for this bill period
        external_payments = ExternalPayment.objects.filter(
            operator       = bill.operator,
            shop           = bill.shop,
            billing_period = bill.billing_period,
            status         = 'verified',
        )
        if external_payments.exists():
            ep_total        = external_payments.aggregate(
                total=Sum('verified_amount')
            )['total'] or 0
            operator_amount = ep_total
            operator_method = 'External Payment'
            external_payment_obj = external_payments.first()

    # Calculate variance
    # Positive = operator underpaid
    # Negative = operator overpaid
    variance = bill.total - operator_amount

    # Determine match status
    if bill.status == 'verified' and variance == 0:
        match_status = ReconciliationRecord.MatchStatus.MATCH
    elif bill.status in ['paid', 'verified']:
        match_status = ReconciliationRecord.MatchStatus.UNVERIFIED
    elif operator_amount > 0 and variance == 0:
        match_status = ReconciliationRecord.MatchStatus.MATCH
    else:
        match_status = ReconciliationRecord.MatchStatus.GAP

    # Create or update the reconciliation record
    record, created = ReconciliationRecord.objects.update_or_create(
        bill = bill,
        defaults = {
            'operator':          bill.operator,
            'shop':              bill.shop,
            'billing_period':    bill.billing_period,
            'iscooa_amount':     bill.total,
            'operator_amount':   operator_amount,
            'operator_method':   operator_method,
            'paid_ref':          paid_ref,
            'external_payment':  external_payment_obj,
            'variance':          variance,
            'match_status':      match_status,
        }
    )
    return record


def reconcile_period(billing_period):
    """
    Reconciles all bills for a given billing period.
    Creates or updates the PeriodSummary.
    Returns the summary record.
    """
    bills = Bill.objects.filter(billing_period=billing_period)

    # Reconcile each bill
    for bill in bills:
        reconcile_bill(bill)

    # Build period summary
    records = ReconciliationRecord.objects.filter(
        billing_period=billing_period
    )

    total_bills      = records.count()
    matched_count    = records.filter(
        match_status=ReconciliationRecord.MatchStatus.MATCH
    ).count()
    unverified_count = records.filter(
        match_status=ReconciliationRecord.MatchStatus.UNVERIFIED
    ).count()
    gap_count        = records.filter(
        match_status=ReconciliationRecord.MatchStatus.GAP
    ).count()

    totals = records.aggregate(
        total_billed   = Sum('iscooa_amount'),
        total_paid     = Sum('operator_amount'),
        total_variance = Sum('variance'),
    )

    total_billed   = totals['total_billed']   or 0
    total_paid     = totals['total_paid']     or 0
    total_variance = totals['total_variance'] or 0

    # External payments for the period
    external_payments = ExternalPayment.objects.filter(
        billing_period = billing_period,
        status         = 'verified',
    )
    ep_count  = external_payments.count()
    ep_amount = external_payments.aggregate(
        total=Sum('verified_amount')
    )['total'] or 0

    # Settlement percentage
    settlement_pct = 0.00
    if total_billed > 0:
        settlement_pct = round(
            (total_paid / total_billed) * 100, 2
        )

    # Create or update period summary
    summary, _ = PeriodSummary.objects.update_or_create(
        billing_period = billing_period,
        defaults = {
            'total_bills':              total_bills,
            'matched_count':            matched_count,
            'unverified_count':         unverified_count,
            'gap_count':                gap_count,
            'total_billed':             total_billed,
            'total_paid':               total_paid,
            'total_variance':           total_variance,
            'external_payments_count':  ep_count,
            'external_payments_amount': ep_amount,
            'settlement_percentage':    settlement_pct,
        }
    )
    return summary