import uuid
from django.db import models


class Association(models.Model):
    """
    Top-level tenant record.
    Every association on the platform gets one record here.
    All data on the platform is scoped to an association.
    """
    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name            = models.CharField(max_length=200)
    # e.g. ISCOOA — Ikota Shopping Complex Owners and Operators Association

    slug            = models.SlugField(max_length=50, unique=True)
    # e.g. iscooa — used in URLs and identifiers

    short_name      = models.CharField(max_length=50)
    # e.g. ISCOOA — used in member numbers and short references

    location        = models.CharField(max_length=200, blank=True)
    # e.g. Ikota Shopping Complex, VGC, Lagos

    is_active       = models.BooleanField(default=True)
    launched_at     = models.DateField(null=True, blank=True)

    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'associations'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.slug})"


class AssociationConfig(models.Model):
    """
    Configuration for each association.
    Controls business rules, branding and financial settings.
    One config record per association.
    """
    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    association     = models.OneToOneField(
                        Association,
                        on_delete=models.CASCADE,
                        related_name='config'
                      )

    # ── Member Number ──────────────────────────────────────────────
    member_prefix   = models.CharField(max_length=20, default='MEMBER')
    # e.g. ISCOOA → generates ISCOOA-2026-0001

    # ── Financial Rules (all amounts in kobo) ──────────────────────
    subscription_rate = models.BigIntegerField(default=100000)
    # ₦1,000 = 100000 kobo — monthly fee per shop

    bot_threshold   = models.BigIntegerField(default=500000000)
    # ₦5,000,000 = 500000000 kobo — expenses above this go to BOT

    # Revenue split — must add up to 100
    association_share = models.IntegerField(default=20)
    # Percentage the association earns e.g. 20%
    platform_share  = models.IntegerField(default=80)
    # Percentage Iprolance earns e.g. 80%

    # ── Branding ───────────────────────────────────────────────────
    logo_url        = models.URLField(blank=True)
    primary_color   = models.CharField(max_length=10, default='#1a3a5c')
    secondary_color = models.CharField(max_length=10, default='#c9a84c')
    # Navy and gold defaults matching ISCOOA brief

    # ── Contact & Legal ────────────────────────────────────────────
    contact_email   = models.EmailField(blank=True)
    contact_phone   = models.CharField(max_length=20, blank=True)
    website         = models.URLField(blank=True)
    footer_text     = models.CharField(
                        max_length=200,
                        default='Powered by Cool Microfinance Bank · Developed by Iprolance LLC'
                      )

    # ── Wallet Provider ────────────────────────────────────────────
    wallet_provider = models.CharField(max_length=100, default='Cool Microfinance Bank')
    wallet_provider_short = models.CharField(max_length=30, default='Cool MFB')

    # ── Toilet Revenue ─────────────────────────────────────────────
    toilet_association_share = models.IntegerField(default=100)
    # Default 100% to association — Iprolance takes nothing

    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'association_configs'

    def __str__(self):
        return f"Config for {self.association.name}"

    @property
    def subscription_rate_naira(self):
        return self.subscription_rate / 100

    @property
    def bot_threshold_naira(self):
        return self.bot_threshold / 100

    def generate_member_number(self, sequence_number):
        """
        Generate a member number for this association.
        e.g. ISCOOA-2026-0001 or BMTA-2026-0001
        """
        from django.utils import timezone
        year = timezone.now().year
        return f"{self.member_prefix}-{year}-{sequence_number:04d}"