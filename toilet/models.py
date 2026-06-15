import uuid
from django.db import models
from accounts.models import User
from shops.models import Shop


class ToiletPricing(models.Model):
    """
    Configurable toilet pricing.
    Editable by ISCOOA Treasurer from the admin panel.
    Only one active pricing record at a time.
    """

    class Plan(models.TextChoices):
        DAILY     = 'daily',     'Daily Pass'
        MONTHLY   = 'monthly',   'Monthly'
        QUARTERLY = 'quarterly', 'Quarterly'
        ANNUAL    = 'annual',    'Annual'

    # Default prices in kobo as per the brief
    # Daily ₦100, Monthly ₦1,000, Quarterly ₦2,500, Annual ₦9,000
    daily_kobo     = models.BigIntegerField(default=10000)
    monthly_kobo   = models.BigIntegerField(default=100000)
    quarterly_kobo = models.BigIntegerField(default=250000)
    annual_kobo    = models.BigIntegerField(default=900000)

    is_active      = models.BooleanField(default=True)
    updated_by     = models.ForeignKey(
                        User,
                        on_delete=models.SET_NULL,
                        null=True, blank=True,
                        related_name='toilet_pricing_updates'
                      )
    updated_at     = models.DateTimeField(auto_now=True)
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'toilet_pricing'

    def __str__(self):
        return f"Toilet Pricing (Daily: ₦{self.daily_kobo/100}, Monthly: ₦{self.monthly_kobo/100})"

    def get_price(self, plan):
        """Return price in kobo for a given plan."""
        prices = {
            'daily':     self.daily_kobo,
            'monthly':   self.monthly_kobo,
            'quarterly': self.quarterly_kobo,
            'annual':    self.annual_kobo,
        }
        return prices.get(plan, 0)

    @property
    def daily_naira(self):
        return self.daily_kobo / 100

    @property
    def monthly_naira(self):
        return self.monthly_kobo / 100

    @property
    def quarterly_naira(self):
        return self.quarterly_kobo / 100

    @property
    def annual_naira(self):
        return self.annual_kobo / 100


class ToiletSubscription(models.Model):
    """
    Per-person toilet access subscription.
    Registered by operators for their staff or customers.
    100% of revenue goes to ISCOOA — no Iprolance cut.
    """

    class PersonType(models.TextChoices):
        STAFF    = 'staff',    'Staff'
        CUSTOMER = 'customer', 'Customer'

    class Plan(models.TextChoices):
        DAILY     = 'daily',     'Daily Pass'
        MONTHLY   = 'monthly',   'Monthly'
        QUARTERLY = 'quarterly', 'Quarterly'
        ANNUAL    = 'annual',    'Annual'

    class Status(models.TextChoices):
        ACTIVE  = 'active',  'Active'
        EXPIRED = 'expired', 'Expired'

    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Who registered this subscription
    registered_by   = models.ForeignKey(
                        User,
                        on_delete=models.CASCADE,
                        related_name='toilet_registrations'
                      )
    shop            = models.ForeignKey(
                        Shop,
                        on_delete=models.CASCADE,
                        related_name='toilet_subscriptions'
                      )

    # The person getting toilet access
    full_name       = models.CharField(max_length=200)
    person_type     = models.CharField(
                        max_length=10,
                        choices=PersonType.choices,
                        default=PersonType.STAFF
                      )

    plan            = models.CharField(max_length=20, choices=Plan.choices)
    amount          = models.BigIntegerField()
    # stored in kobo — 100% ISCOOA revenue

    # Dates
    start_date      = models.DateField()
    expiry_date     = models.DateField()

    status          = models.CharField(
                        max_length=10,
                        choices=Status.choices,
                        default=Status.ACTIVE
                      )

    # Payment reference
    payment_ref     = models.CharField(max_length=100, blank=True)

    # Unique reference for this person's access
    access_ref      = models.CharField(max_length=30, unique=True, blank=True)
    # e.g. TOILET-2026-0001

    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'toilet_subscriptions'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.full_name} ({self.plan}) — {self.shop.shop_number}"

    @property
    def amount_naira(self):
        return self.amount / 100

    @property
    def is_expired(self):
        from django.utils import timezone
        return self.expiry_date < timezone.now().date()

    def save(self, *args, **kwargs):
        # Auto-generate access ref on first save
        if not self.access_ref:
            count = ToiletSubscription.objects.count() + 1
            self.access_ref = f"TOILET-{self.start_date.year}-{count:04d}"
        super().save(*args, **kwargs)