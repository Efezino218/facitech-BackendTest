import uuid
from django.db import models
from accounts.models import User


class KYCStatus(models.TextChoices):
    DRAFT           = 'draft',           'Draft'
    SUBMITTED       = 'submitted',       'Submitted'
    DOCS_REQUESTED  = 'docs_requested',  'Documents Requested'
    APPROVED        = 'approved',        'Approved'
    REJECTED        = 'rejected',        'Rejected'


class KYCApplication(models.Model):
    """
    One KYC application per operator.
    Multi-step data stored in separate related models below.
    Top-level status and review trail stored here.
    """
    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    operator        = models.OneToOneField(
                        User,
                        on_delete=models.CASCADE,
                        related_name='kyc_application'
                      )
    
    # Association this KYC belongs to
    association     = models.ForeignKey(
                        'associations.Association',
                        on_delete=models.SET_NULL,
                        null=True, blank=True,
                        related_name='kyc_applications'
                      )
    kyc_id          = models.CharField(max_length=20, unique=True)
    # e.g. KYC-001 — auto-generated on submission

    status          = models.CharField(
                        max_length=20,
                        choices=KYCStatus.choices,
                        default=KYCStatus.SUBMITTED
                      )

    # Set when approved
    member_number   = models.CharField(max_length=30, blank=True, null=True)
    approved_by     = models.ForeignKey(
                        User,
                        on_delete=models.SET_NULL,
                        null=True, blank=True,
                        related_name='kyc_approvals'
                      )
    approved_date   = models.DateTimeField(null=True, blank=True)

    # Free text note when docs are requested or rejected
    docs_note       = models.TextField(blank=True)

    submitted_date  = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'kyc_applications'
        ordering = ['-submitted_date']

    def __str__(self):
        return f"{self.kyc_id} — {self.operator.email} ({self.status})"


class KYCReviewNote(models.Model):
    """
    Every review action on a KYC application is appended here.
    Maps to reviewNotes array in the brief.
    """
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(
                    KYCApplication,
                    on_delete=models.CASCADE,
                    related_name='review_notes'
                  )
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    note        = models.TextField()
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'kyc_review_notes'
        ordering = ['created_at']

    def __str__(self):
        return f"Note on {self.application.kyc_id} by {self.reviewed_by}"


class KYCPersonal(models.Model):
    """Step 1 — Personal Identity"""
    application = models.OneToOneField(
                    KYCApplication,
                    on_delete=models.CASCADE,
                    related_name='personal'
                  )
    date_of_birth   = models.DateField(null=True, blank=True)
    gender          = models.CharField(max_length=10, blank=True)
    nin             = models.CharField(max_length=11, blank=True)
    bvn             = models.CharField(max_length=11, blank=True)
    phone           = models.CharField(max_length=20, blank=True)
    email           = models.EmailField(blank=True)
    address         = models.TextField(blank=True)
    id_type         = models.CharField(max_length=30, blank=True)
    id_file         = models.FileField(upload_to='kyc/ids/', null=True, blank=True)
    passport_photo  = models.ImageField(upload_to='kyc/passports/', null=True, blank=True)

    class Meta:
        db_table = 'kyc_personal'


class KYCBusiness(models.Model):
    """Step 2 — Business Profile"""
    application     = models.OneToOneField(
                        KYCApplication,
                        on_delete=models.CASCADE,
                        related_name='business'
                      )
    trading_name    = models.CharField(max_length=200, blank=True)
    nature          = models.CharField(max_length=200, blank=True)
    description     = models.TextField(blank=True)
    cac_number      = models.CharField(max_length=50, blank=True)
    cac_file        = models.FileField(upload_to='kyc/cac/', null=True, blank=True)
    year_started    = models.IntegerField(null=True, blank=True)
    first_year      = models.IntegerField(null=True, blank=True)
    relocated       = models.BooleanField(default=False)

    class Meta:
        db_table = 'kyc_business'


class KYCShop(models.Model):
    """Step 3 — Shops (one record per shop)"""

    class Tenure(models.TextChoices):
        LEASED    = 'leased',    'Leased'
        OWNED     = 'owned',     'Owned'
        SUBLEASED = 'subleased', 'Subleased'

    application     = models.ForeignKey(
                        KYCApplication,
                        on_delete=models.CASCADE,
                        related_name='kyc_shops'
                      )
    shop_number     = models.CharField(max_length=20)
    block           = models.CharField(max_length=5)
    floor           = models.CharField(max_length=20, blank=True)
    size_sqm        = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    tenure          = models.CharField(max_length=20, choices=Tenure.choices, blank=True)
    landlord        = models.CharField(max_length=200, blank=True)
    trading_name    = models.CharField(max_length=200, blank=True)
    nature          = models.CharField(max_length=200, blank=True)
    description     = models.TextField(blank=True)
    shop_photo      = models.ImageField(upload_to='kyc/shops/', null=True, blank=True)

    class Meta:
        db_table = 'kyc_shops'

    def __str__(self):
        return f"{self.shop_number} — {self.application.kyc_id}"


class KYCIscooaStanding(models.Model):
    """Step 4 — ISCOOA Standing"""
    application     = models.OneToOneField(
                        KYCApplication,
                        on_delete=models.CASCADE,
                        related_name='iscooa_standing'
                      )
    current_position    = models.CharField(max_length=100, blank=True, default='None')
    previous_positions  = models.TextField(blank=True)
    years_as_member     = models.IntegerField(default=0)
    has_disputes        = models.BooleanField(default=False)
    dispute_note        = models.TextField(blank=True)

    class Meta:
        db_table = 'kyc_iscooa_standing'


class KYCStaff(models.Model):
    """Step 5 — Staff info"""
    application         = models.OneToOneField(
                            KYCApplication,
                            on_delete=models.CASCADE,
                            related_name='staff_info'
                          )
    total_staff_count   = models.IntegerField(default=0)
    intends_to_register = models.BooleanField(default=False)

    class Meta:
        db_table = 'kyc_staff'


class KYCNextOfKin(models.Model):
    """Step 6 — Next of Kin"""
    application = models.OneToOneField(
                    KYCApplication,
                    on_delete=models.CASCADE,
                    related_name='next_of_kin'
                  )
    name        = models.CharField(max_length=200, blank=True)
    relation    = models.CharField(max_length=100, blank=True)
    phone       = models.CharField(max_length=20, blank=True)
    address     = models.TextField(blank=True)

    class Meta:
        db_table = 'kyc_next_of_kin'


class KYCGuarantor(models.Model):
    """Step 7 — Guarantor (optional but recommended)"""
    application = models.OneToOneField(
                    KYCApplication,
                    on_delete=models.CASCADE,
                    related_name='guarantor'
                  )
    name        = models.CharField(max_length=200, blank=True)
    relation    = models.CharField(max_length=100, blank=True)
    phone       = models.CharField(max_length=20, blank=True)

    class Meta:
        db_table = 'kyc_guarantor'


class KYCFinance(models.Model):
    """Step 8 — Finance"""
    application = models.OneToOneField(
                    KYCApplication,
                    on_delete=models.CASCADE,
                    related_name='finance'
                  )
    bank        = models.CharField(max_length=100, blank=True)
    account_no  = models.CharField(max_length=20, blank=True)
    account_name = models.CharField(max_length=200, blank=True)
    tin         = models.CharField(max_length=20, blank=True)

    class Meta:
        db_table = 'kyc_finance'


class KYCEmergencyContact(models.Model):
    """Step 9 — Emergency Contact"""
    application = models.OneToOneField(
                    KYCApplication,
                    on_delete=models.CASCADE,
                    related_name='emergency_contact'
                  )
    name        = models.CharField(max_length=200, blank=True)
    relation    = models.CharField(max_length=100, blank=True)
    phone       = models.CharField(max_length=20, blank=True)

    class Meta:
        db_table = 'kyc_emergency_contact'


class KYCDocuments(models.Model):
    """Step 10 — Document uploads"""
    application     = models.OneToOneField(
                        KYCApplication,
                        on_delete=models.CASCADE,
                        related_name='documents'
                      )
    passport_photo  = models.ImageField(upload_to='kyc/docs/passport/', null=True, blank=True)
    gov_id          = models.FileField(upload_to='kyc/docs/gov_id/', null=True, blank=True)
    cac_certificate = models.FileField(upload_to='kyc/docs/cac/', null=True, blank=True)
    tenancy_lease   = models.FileField(upload_to='kyc/docs/tenancy/', null=True, blank=True)
    shop_photo      = models.ImageField(upload_to='kyc/docs/shop/', null=True, blank=True)

    class Meta:
        db_table = 'kyc_documents'


class KYCDeclaration(models.Model):
    """Step 11 — NDPR consent + declaration + e-signature"""
    application     = models.OneToOneField(
                        KYCApplication,
                        on_delete=models.CASCADE,
                        related_name='declaration'
                      )
    ndpr_consent    = models.BooleanField(default=False)
    declaration     = models.BooleanField(default=False)
    signature       = models.CharField(max_length=200, blank=True)
    sign_date       = models.DateField(null=True, blank=True)

    class Meta:
        db_table = 'kyc_declaration'