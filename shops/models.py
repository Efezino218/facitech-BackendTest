import uuid
from django.db import models
from accounts.models import User


class Shop(models.Model):
    """
    Approved shop records linked to an operator.
    Created when KYC is approved or added later by the operator.
    """

    class Block(models.TextChoices):
        A = 'A', 'Block A'
        B = 'B', 'Block B'
        C = 'C', 'Block C'
        D = 'D', 'Block D'
        E = 'E', 'Block E'
        F = 'F', 'Block F'
        G = 'G', 'Block G'
        H = 'H', 'Block H'

    class Tenure(models.TextChoices):
        LEASED    = 'leased',    'Leased'
        OWNED     = 'owned',     'Owned'
        SUBLEASED = 'subleased', 'Subleased'

    class ElectricityType(models.TextChoices):
        METERED   = 'metered',   'Metered'
        FLAT_RATE = 'flat_rate', 'Flat Rate'

    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    operator        = models.ForeignKey(
                        User,
                        on_delete=models.CASCADE,
                        related_name='shops'
                      )
    
    # Association this shop belongs to
    association     = models.ForeignKey(
                        'associations.Association',
                        on_delete=models.SET_NULL,
                        null=True, blank=True,
                        related_name='shops'
                      )


    # Shop identity
    shop_number     = models.CharField(max_length=20, unique=True)
    # e.g. B-11 — must be unique across the entire complex
    block           = models.CharField(max_length=5, choices=Block.choices)
    floor           = models.CharField(max_length=30, blank=True)
    size_sqm        = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)

    # Tenure info
    tenure          = models.CharField(max_length=20, choices=Tenure.choices, default=Tenure.LEASED)
    landlord        = models.CharField(max_length=200, blank=True)

    # Business info for this specific shop
    trading_name    = models.CharField(max_length=200, blank=True)
    nature          = models.CharField(max_length=200, blank=True)
    description     = models.TextField(blank=True)

    # Billing config
    electricity_type = models.CharField(
                        max_length=20,
                        choices=ElectricityType.choices,
                        default=ElectricityType.FLAT_RATE
                       )

    # ISCOOA position held at this shop
    # e.g. operator is Treasurer and this is the shop they declared
    iscooa_position = models.CharField(max_length=50, blank=True)

    # Media
    shop_photo      = models.ImageField(upload_to='shops/photos/', null=True, blank=True)

    is_active       = models.BooleanField(default=True)
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'shops'
        ordering = ['block', 'shop_number']

    def __str__(self):
        return f"{self.shop_number} — {self.operator.full_name}"


class StaffMember(models.Model):
    """
    Staff sub-accounts registered by an operator.
    Up to 5 staff per operator on the Basic tier.
    Staff are linked to a specific shop.
    """

    class StaffRole(models.TextChoices):
        SALES_ASSOCIATE = 'sales_associate', 'Sales Associate'
        CASHIER         = 'cashier',         'Cashier'
        STORE_KEEPER    = 'store_keeper',    'Store Keeper'
        SECURITY        = 'security',        'Security'
        OTHER           = 'other',           'Other'

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    operator    = models.ForeignKey(
                    User,
                    on_delete=models.CASCADE,
                    related_name='staff_members'
                  )
    shop        = models.ForeignKey(
                    Shop,
                    on_delete=models.CASCADE,
                    related_name='staff'
                  )
    full_name   = models.CharField(max_length=200)
    role        = models.CharField(max_length=30, choices=StaffRole.choices, default=StaffRole.OTHER)
    phone       = models.CharField(max_length=20, blank=True)
    email       = models.EmailField(blank=True)
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'staff_members'
        ordering = ['full_name']

    def __str__(self):
        return f"{self.full_name} ({self.role}) — {self.shop.shop_number}"