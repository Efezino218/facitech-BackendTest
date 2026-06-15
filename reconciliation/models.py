import uuid
from django.db import models
from accounts.models import User
from shops.models import Shop
from bills.models import Bill, ExternalPayment


class ReconciliationRecord(models.Model):
    """
    Dual-party ledger entry.
    Cross-references ISCOOA billing record against
    operator payment record for each invoice.
    Status: match, unverified, gap.
    """

    class MatchStatus(models.TextChoices):
        MATCH      = 'match',      'Match'
        UNVERIFIED = 'unverified', 'Unverified'
        GAP        = 'gap',        'Gap'

    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # The bill being reconciled
    bill            = models.OneToOneField(
                        Bill,
                        on_delete=models.CASCADE,
                        related_name='reconciliation'
                      )
    operator        = models.ForeignKey(
                        User,
                        on_delete=models.CASCADE,
                        related_name='reconciliation_records'
                      )
    shop            = models.ForeignKey(
                        Shop,
                        on_delete=models.CASCADE,
                        related_name='reconciliation_records'
                      )
    billing_period  = models.CharField(max_length=20)

    # ISCOOA side — what ISCOOA says was billed
    iscooa_amount   = models.BigIntegerField(default=0)
    # stored in kobo

    # Operator side — what the operator paid
    operator_amount = models.BigIntegerField(default=0)
    # stored in kobo

    # How the operator paid
    operator_method = models.CharField(max_length=50, blank=True)
    # e.g. 'Cool MFB Wallet' or 'External Payment'

    # Payment reference from operator side
    paid_ref        = models.CharField(max_length=100, blank=True)

    # External payment reference if applicable
    external_payment = models.ForeignKey(
                        ExternalPayment,
                        on_delete=models.SET_NULL,
                        null=True, blank=True,
                        related_name='reconciliation_records'
                      )

    # Variance — difference between ISCOOA and operator amounts
    variance        = models.BigIntegerField(default=0)
    # positive = operator underpaid, negative = operator overpaid

    # Match status
    match_status    = models.CharField(
                        max_length=15,
                        choices=MatchStatus.choices,
                        default=MatchStatus.UNVERIFIED
                      )

    # Notes from ISCOOA
    notes           = models.TextField(blank=True)

    # Who last reconciled this record
    reconciled_by   = models.ForeignKey(
                        User,
                        on_delete=models.SET_NULL,
                        null=True, blank=True,
                        related_name='reconciled_records'
                      )
    reconciled_at   = models.DateTimeField(null=True, blank=True)

    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'reconciliation_records'
        ordering = ['-billing_period', 'shop__shop_number']

    def __str__(self):
        return (
            f"{self.bill.invoice_id} — "
            f"{self.shop.shop_number} "
            f"({self.match_status})"
        )

    @property
    def iscooa_amount_naira(self):
        return self.iscooa_amount / 100

    @property
    def operator_amount_naira(self):
        return self.operator_amount / 100

    @property
    def variance_naira(self):
        return self.variance / 100


class PeriodSummary(models.Model):
    """
    Monthly reconciliation summary.
    Aggregated view per billing period.
    """
    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    billing_period  = models.CharField(max_length=20, unique=True)
    # e.g. "2026-05"

    # Counts
    total_bills     = models.IntegerField(default=0)
    matched_count   = models.IntegerField(default=0)
    unverified_count = models.IntegerField(default=0)
    gap_count       = models.IntegerField(default=0)

    # Amounts in kobo
    total_billed    = models.BigIntegerField(default=0)
    total_paid      = models.BigIntegerField(default=0)
    total_variance  = models.BigIntegerField(default=0)

    # External payments for the period
    external_payments_count  = models.IntegerField(default=0)
    external_payments_amount = models.BigIntegerField(default=0)

    # Settlement percentage
    settlement_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00
    )

    last_updated    = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'period_summaries'
        ordering = ['-billing_period']

    def __str__(self):
        return (
            f"Period {self.billing_period} — "
            f"{self.settlement_percentage}% settled"
        )

    @property
    def total_billed_naira(self):
        return self.total_billed / 100

    @property
    def total_paid_naira(self):
        return self.total_paid / 100

    @property
    def total_variance_naira(self):
        return self.total_variance / 100