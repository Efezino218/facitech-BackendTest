import uuid
from django.db import models
from accounts.models import User


class RevenueWalletType(models.TextChoices):
    ASSOCIATION = 'association', 'Association Revenue'
    PLATFORM    = 'platform',   'Platform Revenue (Iprolance)'


class RevenueWallet(models.Model):
    """
    Tracks accumulated revenue for each party.
    One wallet per association (their 20% share).
    One global wallet for Iprolance (their 80% share).

    This is NOT a real bank account — it tracks what is
    owed to each party from collected payments.
    Actual bank transfers happen via WithdrawalRequest.
    """
    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    wallet_type     = models.CharField(
                        max_length=15,
                        choices=RevenueWalletType.choices,
                    )

    # For association wallets — which association owns this
    # Null for the Iprolance platform wallet
    association     = models.OneToOneField(
                        'associations.Association',
                        on_delete=models.CASCADE,
                        related_name='revenue_wallet',
                        null=True, blank=True,
                      )

    # Display name
    name            = models.CharField(max_length=200)
    # e.g. "ISCOOA Revenue" or "Iprolance Platform Revenue"

    # Balance in kobo — total accumulated, not yet withdrawn
    balance         = models.BigIntegerField(default=0)

    # Total ever earned (never decreases)
    total_earned    = models.BigIntegerField(default=0)

    # Total ever withdrawn
    total_withdrawn = models.BigIntegerField(default=0)

    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'revenue_wallets'

    def __str__(self):
        return f"{self.name} — Balance: ₦{self.balance_naira:,.2f}"

    @property
    def balance_naira(self):
        return self.balance / 100

    @property
    def total_earned_naira(self):
        return self.total_earned / 100

    @property
    def total_withdrawn_naira(self):
        return self.total_withdrawn / 100

    def credit(self, amount_kobo, source_type, source_ref, description=''):
        """
        Credit this revenue wallet.
        Creates a RevenueTransaction record.
        """
        self.balance        += amount_kobo
        self.total_earned   += amount_kobo
        self.save()

        return RevenueTransaction.objects.create(
            revenue_wallet = self,
            transaction_type = RevenueTransactionType.CREDIT,
            amount         = amount_kobo,
            source_type    = source_type,
            source_ref     = source_ref,
            description    = description,
        )

    def debit(self, amount_kobo, description='', ref=''):
        """
        Debit this revenue wallet on withdrawal.
        """
        if self.balance < amount_kobo:
            raise ValueError(
                f'Insufficient revenue balance. '
                f'Available: ₦{self.balance_naira:,.2f}, '
                f'Requested: ₦{amount_kobo/100:,.2f}'
            )
        self.balance          -= amount_kobo
        self.total_withdrawn  += amount_kobo
        self.save()

        return RevenueTransaction.objects.create(
            revenue_wallet   = self,
            transaction_type = RevenueTransactionType.DEBIT,
            amount           = amount_kobo,
            source_type      = 'withdrawal',
            source_ref       = ref,
            description      = description,
        )


class RevenueSourceType(models.TextChoices):
    SUBSCRIPTION = 'subscription', 'Subscription Fee'
    ADVERT       = 'advert',       'Advert Fee'
    TOILET       = 'toilet',       'Toilet Subscription'
    BILL         = 'bill',         'HFP Bill Payment'
    WITHDRAWAL   = 'withdrawal',   'Withdrawal'
    ADJUSTMENT   = 'adjustment',   'Manual Adjustment'


class RevenueTransactionType(models.TextChoices):
    CREDIT = 'credit', 'Credit'
    DEBIT  = 'debit',  'Debit'


class RevenueTransaction(models.Model):
    """
    Every credit and debit to a revenue wallet is recorded here.
    Full audit trail of all revenue movements.
    """
    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    revenue_wallet  = models.ForeignKey(
                        RevenueWallet,
                        on_delete=models.CASCADE,
                        related_name='transactions'
                      )

    transaction_type = models.CharField(
                        max_length=10,
                        choices=RevenueTransactionType.choices,
                      )

    amount          = models.BigIntegerField()
    # in kobo

    source_type     = models.CharField(
                        max_length=20,
                        choices=RevenueSourceType.choices,
                      )
    source_ref      = models.CharField(max_length=100, blank=True)
    # e.g. SUB-payment-ref, INV-2606-001, EXP-001

    description     = models.TextField(blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'revenue_transactions'
        ordering = ['-created_at']

    def __str__(self):
        return (
            f"{self.transaction_type} ₦{self.amount/100:,.2f} "
            f"— {self.revenue_wallet.name} ({self.source_type})"
        )

    @property
    def amount_naira(self):
        return self.amount / 100


class RevenueDistribution(models.Model):
    """
    Records every revenue split event.
    Created whenever an operator makes a payment.
    Shows exactly how much went to association vs platform.
    """

    class PaymentType(models.TextChoices):
        SUBSCRIPTION     = 'subscription',      'Subscription Fee'
        ADVERT           = 'advert',            'Advert Fee'
        TOILET           = 'toilet',            'Toilet Subscription'
        BILL             = 'bill',              'HFP Bill Payment'
        EXTERNAL_PAYMENT = 'external_payment',  'External Payment'
        WITHDRAWAL       = 'withdrawal',        'Withdrawal'
        ADJUSTMENT       = 'adjustment',        'Manual Adjustment'

    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Which association this payment came from
    association     = models.ForeignKey(
                        'associations.Association',
                        on_delete=models.CASCADE,
                        related_name='revenue_distributions',
                      )

    # Who paid
    operator        = models.ForeignKey(
                        User,
                        on_delete=models.CASCADE,
                        related_name='revenue_distributions',
                      )

    payment_type    = models.CharField(
                        max_length=16,
                        choices=PaymentType.choices,
                      )

    # Source reference — e.g. subscription payment ref or invoice ID
    source_ref      = models.CharField(max_length=100, blank=True)

    # Total amount paid by operator in kobo
    total_amount    = models.BigIntegerField()

    # How it was split
    association_share_pct = models.IntegerField()
    # e.g. 20

    platform_share_pct    = models.IntegerField()
    # e.g. 80

    association_amount    = models.BigIntegerField()
    # In kobo — what association receives

    platform_amount       = models.BigIntegerField()
    # In kobo — what Iprolance receives

    # For toilet — 100% to association, 0% to platform
    note            = models.TextField(blank=True)

    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'revenue_distributions'
        ordering = ['-created_at']

    def __str__(self):
        return (
            f"{self.get_payment_type_display()} — "
            f"{self.operator.email} — "
            f"Total: ₦{self.total_amount/100:,.2f} "
            f"(Assoc: ₦{self.association_amount/100:,.2f} | "
            f"Platform: ₦{self.platform_amount/100:,.2f})"
        )

    @property
    def total_amount_naira(self):
        return self.total_amount / 100

    @property
    def association_amount_naira(self):
        return self.association_amount / 100

    @property
    def platform_amount_naira(self):
        return self.platform_amount / 100




class WithdrawalRequest(models.Model):
    """
    Withdrawal request from a revenue wallet.
    Flow:
        Treasurer requests → President approves → Super Admin processes

    For association wallets: Treasurer requests, President approves.
    For platform wallet: Super Admin requests and processes directly.
    """

    class Status(models.TextChoices):
        PENDING   = 'pending',   'Pending President Approval'
        APPROVED  = 'approved',  'Approved — Awaiting Processing'
        PROCESSED = 'processed', 'Processed — Funds Transferred'
        REJECTED  = 'rejected',  'Rejected'

    class TransferMethod(models.TextChoices):
        BANK_TRANSFER = 'bank_transfer', 'Direct Bank Transfer'
        PAYSTACK      = 'paystack',      'Paystack Transfer'
        COOL_MFB      = 'cool_mfb',      'Cool MFB Transfer'
        CHEQUE        = 'cheque',        'Cheque'

    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    withdrawal_ref  = models.CharField(max_length=30, unique=True, blank=True)
    # e.g. WDR-2026-0001

    revenue_wallet  = models.ForeignKey(
                        RevenueWallet,
                        on_delete=models.CASCADE,
                        related_name='withdrawal_requests',
                      )

    # Who made this request
    requested_by    = models.ForeignKey(
                        User,
                        on_delete=models.SET_NULL,
                        null=True,
                        related_name='withdrawal_requests',
                      )
    requested_at    = models.DateTimeField(auto_now_add=True)

    amount          = models.BigIntegerField()
    # Amount requested in kobo

    reason          = models.TextField(blank=True)
    # Purpose of withdrawal e.g. "Monthly payout to ISCOOA secretariat account"

    # Bank details for the transfer
    bank_name       = models.CharField(max_length=100, blank=True)
    account_number  = models.CharField(max_length=20, blank=True)
    account_name    = models.CharField(max_length=200, blank=True)

    status          = models.CharField(
                        max_length=15,
                        choices=Status.choices,
                        default=Status.PENDING,
                      )

    # President approval
    approved_by     = models.ForeignKey(
                        User,
                        on_delete=models.SET_NULL,
                        null=True, blank=True,
                        related_name='approved_withdrawals',
                      )
    approved_at     = models.DateTimeField(null=True, blank=True)
    approval_note   = models.TextField(blank=True)

    # Rejection
    rejected_by     = models.ForeignKey(
                        User,
                        on_delete=models.SET_NULL,
                        null=True, blank=True,
                        related_name='rejected_withdrawals',
                      )
    rejected_at     = models.DateTimeField(null=True, blank=True)
    rejection_note  = models.TextField(blank=True)

    # Processing — done by Super Admin
    processed_by    = models.ForeignKey(
                        User,
                        on_delete=models.SET_NULL,
                        null=True, blank=True,
                        related_name='processed_withdrawals',
                      )
    processed_at    = models.DateTimeField(null=True, blank=True)
    transfer_method = models.CharField(
                        max_length=20,
                        choices=TransferMethod.choices,
                        blank=True,
                      )
    transfer_ref    = models.CharField(max_length=100, blank=True)
    # Bank transfer reference or Paystack transfer code

    processing_note = models.TextField(blank=True)

    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'withdrawal_requests'
        ordering = ['-requested_at']

    def __str__(self):
        return (
            f"{self.withdrawal_ref} — "
            f"{self.revenue_wallet.name} "
            f"₦{self.amount_naira:,.2f} ({self.status})"
        )

    def save(self, *args, **kwargs):
        if not self.withdrawal_ref:
            count = WithdrawalRequest.objects.count() + 1
            from django.utils import timezone
            year = timezone.now().year
            self.withdrawal_ref = f"WDR-{year}-{count:04d}"
        super().save(*args, **kwargs)

    @property
    def amount_naira(self):
        return self.amount / 100