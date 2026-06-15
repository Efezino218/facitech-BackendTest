import uuid
from django.db import models
from accounts.models import User
from shops.models import Shop


class Bill(models.Model):
    """
    HFP invoices raised monthly by ISCOOA Treasurer.
    One bill per shop per billing period.
    All amounts stored in kobo (integer) as per the brief.
    """

    class Status(models.TextChoices):
        UNPAID   = 'unpaid',   'Unpaid'
        PAID     = 'paid',     'Paid (Pending Verification)'
        VERIFIED = 'verified', 'Verified'

    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice_id      = models.CharField(max_length=30, unique=True)
    # e.g. INV-2605-001

    shop            = models.ForeignKey(
                        Shop,
                        on_delete=models.CASCADE,
                        related_name='bills'
                      )
    operator        = models.ForeignKey(
                        User,
                        on_delete=models.CASCADE,
                        related_name='bills'
                      )

    # Association this bill belongs to
    association     = models.ForeignKey(
                        'associations.Association',
                        on_delete=models.SET_NULL,
                        null=True, blank=True,
                        related_name='bills'
                      )



    # Billing period
    billing_period  = models.CharField(max_length=20)
    # e.g. "2026-05" (YYYY-MM)

    # Bill line items — all stored in kobo
    management_fee  = models.BigIntegerField(default=0)
    # kobo e.g. 500000 = ₦5,000
    maintenance_levy = models.BigIntegerField(default=0)
    electricity     = models.BigIntegerField(default=0)
    water           = models.BigIntegerField(default=0)
    vat             = models.BigIntegerField(default=0)
    # VAT is 7.5% of subtotal — calculated on save
    total           = models.BigIntegerField(default=0)
    # total = sum of all line items including VAT

    status          = models.CharField(
                        max_length=20,
                        choices=Status.choices,
                        default=Status.UNPAID
                      )

    # Payment tracking
    paid_at         = models.DateTimeField(null=True, blank=True)
    paid_ref        = models.CharField(max_length=100, blank=True)
    # Cool MFB transaction reference

    # Verification
    verified_by     = models.ForeignKey(
                        User,
                        on_delete=models.SET_NULL,
                        null=True, blank=True,
                        related_name='verified_bills'
                      )
    verified_at     = models.DateTimeField(null=True, blank=True)

    # Who raised this bill
    raised_by       = models.ForeignKey(
                        User,
                        on_delete=models.SET_NULL,
                        null=True, blank=True,
                        related_name='raised_bills'
                      )

    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'bills'
        ordering = ['-created_at']
        # One bill per shop per period
        unique_together = ['shop', 'billing_period']

    def __str__(self):
        return f"{self.invoice_id} — {self.shop.shop_number} ({self.billing_period})"

    def calculate_totals(self):
        """
        Recalculate VAT and total from line items.
        Call this before saving whenever line items change.
        VAT = 7.5% of subtotal (management + maintenance + electricity + water)
        """
        subtotal    = (
            self.management_fee +
            self.maintenance_levy +
            self.electricity +
            self.water
        )
        self.vat    = int(subtotal * 0.075)
        self.total  = subtotal + self.vat

    def save(self, *args, **kwargs):
        self.calculate_totals()
        super().save(*args, **kwargs)

    @property
    def total_naira(self):
        """Return total in Naira for display."""
        return self.total / 100

    @property
    def is_overdue(self):
        """Simple check — bill is overdue if unpaid after creation."""
        from django.utils import timezone
        if self.status == self.Status.UNPAID:
            days = (timezone.now() - self.created_at).days
            return days > 30
        return False


def generate_invoice_id(billing_period):
    """
    Generate invoice ID like INV-2605-001.
    2605 = year 26, month 05.
    """
    period_short = billing_period.replace('-', '')[2:]
    # e.g. "2026-05" → "2605"
    count = Bill.objects.filter(billing_period=billing_period).count() + 1
    return f"INV-{period_short}-{count:03d}"


class ExternalPayment(models.Model):
    """
    Operator-registered payments for utilities paid
    directly outside the platform.
    Requires ISCOOA verification within 48 hours.
    """

    class Category(models.TextChoices):
        ELECTRICITY_EKEDC   = 'electricity_ekedc',   'Electricity (EKEDC)'
        ELECTRICITY_GENLEVY = 'electricity_genlevy', 'Electricity (Generator Levy)'
        WATER               = 'water',               'Water (Lagos Water Corp)'
        WASTE               = 'waste',               'Waste Management'
        SECURITY            = 'security',            'Security Levy'
        OTHER               = 'other',               'Other Utility'

    class Status(models.TextChoices):
        PENDING  = 'pending',  'Pending Verification'
        VERIFIED = 'verified', 'Verified'
        REJECTED = 'rejected', 'Rejected'

    class PaymentChannel(models.TextChoices):
        BANK_TRANSFER = 'bank_transfer', 'Bank Transfer'
        POS           = 'pos',           'POS'
        CASH          = 'cash',          'Cash'
        ONLINE        = 'online',        'Online Payment'
        USSD          = 'ussd',          'USSD'

    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    operator        = models.ForeignKey(
                        User,
                        on_delete=models.CASCADE,
                        related_name='external_payments'
                      )
    shop            = models.ForeignKey(
                        Shop,
                        on_delete=models.CASCADE,
                        related_name='external_payments'
                      )

    category        = models.CharField(max_length=30, choices=Category.choices)
    amount          = models.BigIntegerField()
    # stored in kobo

    payment_date    = models.DateField()
    billing_period  = models.CharField(max_length=20)
    # e.g. "2026-05"

    channel         = models.CharField(max_length=20, choices=PaymentChannel.choices)
    reference       = models.CharField(max_length=100, blank=True)
    # teller number or transaction ref

    note            = models.TextField(blank=True)
    evidence        = models.FileField(upload_to='bills/evidence/', null=True, blank=True)
    # receipt, teller slip, or screenshot — max 5MB

    status          = models.CharField(
                        max_length=20,
                        choices=Status.choices,
                        default=Status.PENDING
                      )

    # Verification
    verified_by     = models.ForeignKey(
                        User,
                        on_delete=models.SET_NULL,
                        null=True, blank=True,
                        related_name='verified_external_payments'
                      )
    verified_at     = models.DateTimeField(null=True, blank=True)
    verified_amount = models.BigIntegerField(null=True, blank=True)
    # ISCOOA may confirm a different amount than claimed
    rejection_note  = models.TextField(blank=True)

    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'external_payments'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_category_display()} — {self.shop.shop_number} ({self.billing_period})"

    @property
    def amount_naira(self):
        return self.amount / 100