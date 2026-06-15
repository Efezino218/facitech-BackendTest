import uuid
from django.db import models
from accounts.models import User
from shops.models import Shop


class Advert(models.Model):
    """
    Operator-submitted adverts.
    Approval by Secretary General.
    Revenue split: 20% ISCOOA, 80% Iprolance.
    """

    class Category(models.TextChoices):
        PROMO      = 'promo',      'Promo'
        NEW_STOCK  = 'new_stock',  'New Stock'
        VACANCY    = 'vacancy',    'Vacancy'
        SERVICES   = 'services',   'Services'

    class Status(models.TextChoices):
        PENDING  = 'pending',  'Pending Approval'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'

    # Fee structure in kobo as per the brief
    CATEGORY_FEES = {
        'promo':     200000,   # ₦2,000
        'new_stock': 150000,   # ₦1,500
        'vacancy':   100000,   # ₦1,000
        'services':  100000,   # ₦1,000
    }

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    operator    = models.ForeignKey(
                    User,
                    on_delete=models.CASCADE,
                    related_name='adverts'
                  )
    shop        = models.ForeignKey(
                    Shop,
                    on_delete=models.CASCADE,
                    related_name='adverts'
                  )

    headline    = models.CharField(max_length=200)
    category    = models.CharField(max_length=20, choices=Category.choices)
    description = models.TextField()

    # Fee in kobo — auto set from category
    fee         = models.BigIntegerField(default=0)
    iscooa_cut  = models.BigIntegerField(default=0)
    # 20% of fee
    iprolance_cut = models.BigIntegerField(default=0)
    # 80% of fee

    status      = models.CharField(
                    max_length=20,
                    choices=Status.choices,
                    default=Status.PENDING
                  )

    # Approval details
    reviewed_by = models.ForeignKey(
                    User,
                    on_delete=models.SET_NULL,
                    null=True, blank=True,
                    related_name='reviewed_adverts'
                  )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reject_reason = models.TextField(blank=True)

    # Once approved advert goes live
    is_live     = models.BooleanField(default=False)
    live_from   = models.DateTimeField(null=True, blank=True)
    expires_at  = models.DateTimeField(null=True, blank=True)

    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'adverts'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.headline} — {self.operator.email} ({self.status})"

    def save(self, *args, **kwargs):
        # Auto-set fee from category when first created
        if not self.fee:
            self.fee = self.CATEGORY_FEES.get(self.category, 0)
            self.iscooa_cut   = int(self.fee * 0.20)
            self.iprolance_cut = int(self.fee * 0.80)
        super().save(*args, **kwargs)

    @property
    def fee_naira(self):
        return self.fee / 100

    @property
    def iscooa_cut_naira(self):
        return self.iscooa_cut / 100

    @property
    def iprolance_cut_naira(self):
        return self.iprolance_cut / 100