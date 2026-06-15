import uuid
from django.db import models
from accounts.models import User
from shops.models import Shop
from django.utils import timezone


class Dispute(models.Model):
    """
    Operator-raised disputes and facility issues.
    Routes to ISCOOA Disputes & Issues panel.
    Status flow: open → under_review → investigating → resolved
    """

    class Category(models.TextChoices):
        BILL        = 'bill',        'Bill Dispute'
        MAINTENANCE = 'maintenance', 'Maintenance Issue'
        LIFT        = 'lift',        'Lift'
        WATER       = 'water',       'Water Supply'
        SECURITY    = 'security',    'Security'
        CLEANLINESS = 'cleanliness', 'Cleanliness'
        ELECTRICITY = 'electricity', 'Electricity'
        OTHER       = 'other',       'Other'

    class Status(models.TextChoices):
        OPEN          = 'open',          'Open'
        UNDER_REVIEW  = 'under_review',  'Under Review'
        INVESTIGATING = 'investigating', 'Investigating'
        RESOLVED      = 'resolved',      'Resolved'

    class Priority(models.TextChoices):
        LOW    = 'low',    'Low'
        MEDIUM = 'medium', 'Medium'
        HIGH   = 'high',   'High'
        URGENT = 'urgent', 'Urgent'

    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dispute_ref     = models.CharField(max_length=30, unique=True, blank=True)
    # e.g. DISP-2026-0001

    operator        = models.ForeignKey(
                        User,
                        on_delete=models.CASCADE,
                        related_name='disputes'
                      )
    shop            = models.ForeignKey(
                        Shop,
                        on_delete=models.SET_NULL,
                        null=True, blank=True,
                        related_name='disputes'
                      )

    # For bill disputes
    bill_ref        = models.CharField(max_length=30, blank=True)
    # e.g. INV-2605-001

    category        = models.CharField(max_length=20, choices=Category.choices)
    priority        = models.CharField(
                        max_length=10,
                        choices=Priority.choices,
                        default=Priority.MEDIUM
                      )
    subject         = models.CharField(max_length=200)
    description     = models.TextField()

    # Amount in dispute (for bill disputes) in kobo
    amount_in_dispute = models.BigIntegerField(null=True, blank=True)

    status          = models.CharField(
                        max_length=20,
                        choices=Status.choices,
                        default=Status.OPEN
                      )

    # ISCOOA response as they investigate
    response        = models.TextField(blank=True)

    # Who is handling this dispute
    assigned_to     = models.ForeignKey(
                        User,
                        on_delete=models.SET_NULL,
                        null=True, blank=True,
                        related_name='assigned_disputes'
                      )
    resolved_at     = models.DateTimeField(null=True, blank=True)

    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'disputes'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.dispute_ref} — {self.subject} ({self.status})"

    def save(self, *args, **kwargs):
        if not self.dispute_ref:
            count = Dispute.objects.count() + 1
            # Use timezone.now() directly
            current_year = timezone.now().year
            self.dispute_ref = f"DISP-{current_year}-{count:04d}"
        super().save(*args, **kwargs)

    @property
    def amount_in_dispute_naira(self):
        if self.amount_in_dispute:
            return self.amount_in_dispute / 100
        return None


class DisputeUpdate(models.Model):
    """
    Timeline of updates on a dispute.
    Every status change and response is logged here.
    """
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dispute     = models.ForeignKey(
                    Dispute,
                    on_delete=models.CASCADE,
                    related_name='updates'
                  )
    updated_by  = models.ForeignKey(
                    User,
                    on_delete=models.SET_NULL,
                    null=True,
                    related_name='dispute_updates'
                  )
    old_status  = models.CharField(max_length=20, blank=True)
    new_status  = models.CharField(max_length=20, blank=True)
    note        = models.TextField(blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'dispute_updates'
        ordering = ['created_at']

    def __str__(self):
        return f"Update on {self.dispute.dispute_ref} by {self.updated_by}"