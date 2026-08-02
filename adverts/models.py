import uuid
from django.db import models
from accounts.models import User
from shops.models import Shop


class Advert(models.Model):
    """
    Operator-submitted adverts.
    Approval by Secretary General.
    Wallet debited on approval — not on submission.
    Revenue split per association config (default 20/80).
    """

    class Category(models.TextChoices):
        PROMO     = 'promo',     'Promo'
        NEW_STOCK = 'new_stock', 'New Stock'
        VACANCY   = 'vacancy',   'Vacancy'
        SERVICES  = 'services',  'Services'
        GENERAL   = 'general',   'General'

    class Status(models.TextChoices):
        PENDING  = 'pending',  'Pending Approval'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
        EXPIRED  = 'expired',  'Expired'
        OFFLINE  = 'offline',  'Taken Offline'

    # Fee structure in kobo as per the brief
    CATEGORY_FEES = {
        'promo':     200000,   # ₦2,000
        'new_stock': 150000,   # ₦1,500
        'vacancy':   100000,   # ₦1,000
        'services':  100000,   # ₦1,000
        'general':   100000,   # ₦1,000
    }

    # Default duration per category in days
    CATEGORY_DURATION = {
        'promo':     7,
        'new_stock': 7,
        'vacancy':   30,
        'services':  14,
        'general':   7,
    }

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # White-label — which association this advert belongs to
    association = models.ForeignKey(
                    'associations.Association',
                    on_delete=models.CASCADE,
                    related_name='adverts',
                    null=True, blank=True,
                  )

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
    description = models.TextField()
    # description kept — frontend already uses this field name

    category    = models.CharField(max_length=20, choices=Category.choices)

    # Optional image for carousel display
    image_url   = models.URLField(blank=True)
    
    # Optional contact info — shown on the marketplace card
    # Falls back to shop/operator contact if not provided
    contact_phone    = models.CharField(max_length=20, blank=True)
    contact_email    = models.EmailField(blank=True)
    contact_whatsapp = models.CharField(max_length=20, blank=True)
    contact_instagram = models.CharField(max_length=100, blank=True)
    contact_facebook  = models.CharField(max_length=100, blank=True)

    # Duration in days — auto set from category
    duration_days = models.IntegerField(default=7)

    # Fee in kobo — auto set from category in save()
    fee           = models.BigIntegerField(default=0)
    iscooa_cut    = models.BigIntegerField(default=0)
    iprolance_cut = models.BigIntegerField(default=0)

    status      = models.CharField(
                    max_length=20,
                    choices=Status.choices,
                    default=Status.PENDING
                  )

    # Approval details
    reviewed_by   = models.ForeignKey(
                      User,
                      on_delete=models.SET_NULL,
                      null=True, blank=True,
                      related_name='reviewed_adverts'
                    )
    reviewed_at   = models.DateTimeField(null=True, blank=True)
    reject_reason = models.TextField(blank=True)
    # reject_reason kept — frontend already uses this field name

    # Once approved
    is_live     = models.BooleanField(default=False)
    approved_at = models.DateTimeField(null=True, blank=True)
    live_from   = models.DateTimeField(null=True, blank=True)
    # live_from kept from your original model
    expires_at  = models.DateTimeField(null=True, blank=True)

    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'adverts'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.headline} — {self.operator.email} ({self.status})"

    def save(self, *args, **kwargs):
        # Auto-set fee and duration from category on first creation
        if not self.fee:
            self.fee          = self.CATEGORY_FEES.get(self.category, 100000)
            self.duration_days = self.CATEGORY_DURATION.get(self.category, 7)

        # Revenue split is calculated dynamically at approval time
        # not here — because association config may differ per association.
        # iscooa_cut and iprolance_cut are set in ApproveAdvertView.

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

    @property
    def is_expired(self):
        if self.expires_at:
            from django.utils import timezone
            return timezone.now() > self.expires_at
        return False