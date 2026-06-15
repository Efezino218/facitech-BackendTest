import uuid
from django.db import models
from accounts.models import User
from shops.models import Shop


class Penalty(models.Model):
    """
    Penalty notices issued by ISCOOA against operators.
    Common types: Late payment, Unauthorized signage,
    Health and safety violation.
    """

    class PenaltyType(models.TextChoices):
        LATE_PAYMENT        = 'late_payment',        'Late Payment'
        UNAUTHORIZED_SIGNAGE = 'unauthorized_signage', 'Unauthorized Signage'
        HEALTH_SAFETY       = 'health_safety',       'Health and Safety Violation'
        NOISE_POLLUTION     = 'noise_pollution',      'Noise Pollution'
        ILLEGAL_SUBLETTING  = 'illegal_subletting',  'Illegal Subletting'
        TRADING_VIOLATION   = 'trading_violation',   'Trading Violation'
        OTHER               = 'other',               'Other'

    class Status(models.TextChoices):
        UNPAID   = 'unpaid',   'Unpaid'
        PAID     = 'paid',     'Paid'
        WAIVED   = 'waived',   'Waived'
        DISPUTED = 'disputed', 'Disputed'

    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    penalty_ref     = models.CharField(max_length=30, unique=True, blank=True)
    # e.g. PEN-2026-0001

    operator        = models.ForeignKey(
                        User,
                        on_delete=models.CASCADE,
                        related_name='penalties'
                      )
    shop            = models.ForeignKey(
                        Shop,
                        on_delete=models.SET_NULL,
                        null=True, blank=True,
                        related_name='penalties'
                      )

    penalty_type    = models.CharField(max_length=30, choices=PenaltyType.choices)
    description     = models.TextField()
    amount          = models.BigIntegerField()
    # stored in kobo

    issued_date     = models.DateField()
    due_date        = models.DateField()

    status          = models.CharField(
                        max_length=10,
                        choices=Status.choices,
                        default=Status.UNPAID
                      )

    # Who issued this penalty
    issued_by       = models.ForeignKey(
                        User,
                        on_delete=models.SET_NULL,
                        null=True, blank=True,
                        related_name='issued_penalties'
                      )

    # Payment tracking
    paid_at         = models.DateTimeField(null=True, blank=True)
    paid_ref        = models.CharField(max_length=100, blank=True)

    # Waiver details
    waived_by       = models.ForeignKey(
                        User,
                        on_delete=models.SET_NULL,
                        null=True, blank=True,
                        related_name='waived_penalties'
                      )
    waiver_reason   = models.TextField(blank=True)

    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'penalties'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.penalty_ref} — {self.operator.email} ({self.status})"

    def save(self, *args, **kwargs):
        if not self.penalty_ref:
            count = Penalty.objects.count() + 1
            from django.utils import timezone
            year = timezone.now().year
            self.penalty_ref = f"PEN-{year}-{count:04d}"
        super().save(*args, **kwargs)

    @property
    def amount_naira(self):
        return self.amount / 100

    @property
    def is_overdue(self):
        from django.utils import timezone
        if self.status == self.Status.UNPAID:
            return timezone.now().date() > self.due_date
        return False


class ShutdownNotice(models.Model):
    """
    Shop shutdown notices issued by ISCOOA.
    Lifted by ISCOOA after compliance.
    Notifies operator and HFP on lift.
    """

    class Status(models.TextChoices):
        ACTIVE  = 'active',  'Active'
        LIFTED  = 'lifted',  'Lifted'
        PENDING = 'pending', 'Pending Enforcement'

    class Reason(models.TextChoices):
        NON_PAYMENT      = 'non_payment',      'Non Payment of Dues'
        SAFETY_VIOLATION = 'safety_violation', 'Safety Violation'
        ILLEGAL_ACTIVITY = 'illegal_activity', 'Illegal Activity'
        COURT_ORDER      = 'court_order',      'Court Order'
        STRUCTURAL_RISK  = 'structural_risk',  'Structural Risk'
        OTHER            = 'other',            'Other'

    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    shutdown_ref    = models.CharField(max_length=30, unique=True, blank=True)
    # e.g. SDN-2026-0001

    operator        = models.ForeignKey(
                        User,
                        on_delete=models.CASCADE,
                        related_name='shutdowns'
                      )
    shop            = models.ForeignKey(
                        Shop,
                        on_delete=models.CASCADE,
                        related_name='shutdowns'
                      )

    reason          = models.CharField(max_length=30, choices=Reason.choices)
    description     = models.TextField()

    issued_date     = models.DateField()
    status          = models.CharField(
                        max_length=10,
                        choices=Status.choices,
                        default=Status.PENDING
                      )

    # Who issued
    issued_by       = models.ForeignKey(
                        User,
                        on_delete=models.SET_NULL,
                        null=True, blank=True,
                        related_name='issued_shutdowns'
                      )

    # Lift details
    lifted_at       = models.DateTimeField(null=True, blank=True)
    lifted_by       = models.ForeignKey(
                        User,
                        on_delete=models.SET_NULL,
                        null=True, blank=True,
                        related_name='lifted_shutdowns'
                      )
    lift_reason     = models.TextField(blank=True)

    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'shutdown_notices'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.shutdown_ref} — {self.shop.shop_number} ({self.status})"

    def save(self, *args, **kwargs):
        if not self.shutdown_ref:
            count = ShutdownNotice.objects.count() + 1
            from django.utils import timezone
            year = timezone.now().year
            self.shutdown_ref = f"SDN-{year}-{count:04d}"
        super().save(*args, **kwargs)