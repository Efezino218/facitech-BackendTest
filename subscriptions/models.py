import uuid
from django.db import models
from accounts.models import User


class Subscription(models.Model):
    """
    Platform subscription fee per operator.
    Rate: ₦1,000 per shop per month (stored in kobo).
    Month 1 is free (KYC period).
    Billing starts Month 2.
    Revenue split: 20% ISCOOA, 80% Iprolance.
    """

    class Cycle(models.TextChoices):
        MONTHLY   = 'monthly',   'Monthly'
        QUARTERLY = 'quarterly', 'Quarterly (3 months)'
        ANNUAL    = 'annual',    'Annual (12 months)'

    class Status(models.TextChoices):
        ACTIVE    = 'active',    'Active'
        KYC       = 'kyc',       'KYC Period (Month 1 Free)'
        OVERDUE   = 'overdue',   'Overdue'
        SUSPENDED = 'suspended', 'Suspended'

    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    operator        = models.OneToOneField(
                        User,
                        on_delete=models.CASCADE,
                        related_name='subscription'
                      )
    
    # Association this subscription belongs to
    association     = models.ForeignKey(
                        'associations.Association',
                        on_delete=models.SET_NULL,
                        null=True, blank=True,
                        related_name='subscriptions'
                      )

    # Current subscription state
    status          = models.CharField(
                        max_length=20,
                        choices=Status.choices,
                        default=Status.KYC
                      )
    cycle           = models.CharField(
                        max_length=20,
                        choices=Cycle.choices,
                        default=Cycle.MONTHLY
                      )

    # Month tracking
    current_month   = models.IntegerField(default=1)
    # Month 1 = KYC free period. Billing starts Month 2.

    shop_count      = models.IntegerField(default=1)
    # Snapshot of shop count at time of billing

    # Rate constants (in kobo)
    rate_per_shop   = models.BigIntegerField(default=100000)
    # ₦1,000 = 100000 kobo

    # Current period
    period_start    = models.DateField(null=True, blank=True)
    period_end      = models.DateField(null=True, blank=True)
    renewal_date    = models.DateField(null=True, blank=True)

    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'subscriptions'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.operator.email} — Month {self.current_month} ({self.status})"

    @property
    def monthly_fee(self):
        """Monthly fee in kobo."""
        return self.rate_per_shop * self.shop_count

    @property
    def monthly_fee_naira(self):
        return self.monthly_fee / 100


    def get_association_share(self):
        """Get association revenue share percentage from config."""
        try:
            return self.operator.association.config.association_share
        except Exception:
            return 20  # Default 20%

    def get_platform_share(self):
        """Get platform revenue share percentage from config."""
        try:
            return self.operator.association.config.platform_share
        except Exception:
            return 80  # Default 80%

    @property
    def iscooa_cut(self):
        """Association share of monthly fee in kobo."""
        return int(self.monthly_fee * (self.get_association_share() / 100))

    @property
    def iprolance_cut(self):
        """Platform share of monthly fee in kobo."""
        return int(self.monthly_fee * (self.get_platform_share() / 100))


    @property
    def iscooa_cut_naira(self):
        return self.iscooa_cut / 100

    @property
    def iprolance_cut_naira(self):
        return self.iprolance_cut / 100

    def cycle_total(self):
        """Total amount due for selected cycle in kobo."""
        multipliers = {
            self.Cycle.MONTHLY:   1,
            self.Cycle.QUARTERLY: 3,
            self.Cycle.ANNUAL:    12,
        }
        return self.monthly_fee * multipliers.get(self.cycle, 1)

    def cycle_total_naira(self):
        return self.cycle_total() / 100


class SubscriptionPayment(models.Model):
    """
    Individual subscription payment records.
    One record per payment made by an operator.
    """

    class Status(models.TextChoices):
        PAID    = 'paid',    'Paid'
        PENDING = 'pending', 'Pending'
        FAILED  = 'failed',  'Failed'

    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subscription    = models.ForeignKey(
                        Subscription,
                        on_delete=models.CASCADE,
                        related_name='payments'
                      )
    operator        = models.ForeignKey(
                        User,
                        on_delete=models.CASCADE,
                        related_name='subscription_payments'
                      )

    # Period this payment covers e.g. "2026-05"
    period          = models.CharField(max_length=20)
    cycle           = models.CharField(max_length=20)
    shop_count      = models.IntegerField()

    # Amounts in kobo
    amount          = models.BigIntegerField()
    iscooa_cut      = models.BigIntegerField()
    iprolance_cut   = models.BigIntegerField()

    status          = models.CharField(
                        max_length=20,
                        choices=Status.choices,
                        default=Status.PENDING
                      )

    # Cool MFB payment reference
    payment_ref     = models.CharField(max_length=100, blank=True)
    paid_at         = models.DateTimeField(null=True, blank=True)

    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'subscription_payments'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.operator.email} — {self.period} ({self.cycle})"

    @property
    def amount_naira(self):
        return self.amount / 100

    @property
    def iscooa_cut_naira(self):
        return self.iscooa_cut / 100

    @property
    def iprolance_cut_naira(self):
        return self.iprolance_cut / 100