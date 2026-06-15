import uuid
from django.db import models
from accounts.models import User


class WhistleblowerReport(models.Model):
    """
    Anonymous reports submitted by operators.
    Identity is NEVER recorded — only category,
    narrative, date and status stored.
    Visible only to President and Legal Adviser.
    """

    class Category(models.TextChoices):
        FINANCIAL_IRREGULARITY = 'financial_irregularity', 'Financial Irregularity'
        VENDOR_COLLUSION       = 'vendor_collusion',       'Vendor Collusion'
        HARASSMENT             = 'harassment',             'Harassment'
        CORRUPTION             = 'corruption',             'Corruption'
        SAFETY_VIOLATION       = 'safety_violation',       'Safety Violation'
        MISCONDUCT             = 'misconduct',             'Staff Misconduct'
        OTHER                  = 'other',                  'Other'

    class Status(models.TextChoices):
        OPEN          = 'open',          'Open'
        UNDER_REVIEW  = 'under_review',  'Under Review'
        INVESTIGATING = 'investigating', 'Investigating'
        RESOLVED      = 'resolved',      'Resolved'
        ARCHIVED      = 'archived',      'Archived'

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    report_ref  = models.CharField(max_length=30, unique=True, blank=True)
    # e.g. WB-2026-0001

    category    = models.CharField(max_length=30, choices=Category.choices)
    narrative   = models.TextField()
    # The full report text

    status      = models.CharField(
                    max_length=20,
                    choices=Status.choices,
                    default=Status.OPEN
                  )

    # ISCOOA response — visible only to President and Legal Adviser
    response    = models.TextField(blank=True)

    # Who is handling this report
    # NOTE: This is the investigator NOT the submitter
    assigned_to = models.ForeignKey(
                    User,
                    on_delete=models.SET_NULL,
                    null=True, blank=True,
                    related_name='assigned_wb_reports'
                  )

    resolved_at = models.DateTimeField(null=True, blank=True)

    # Submission timestamp — no user link whatsoever
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'whistleblower_reports'
        ordering = ['-submitted_at']

    def __str__(self):
        return f"{self.report_ref} — {self.get_category_display()} ({self.status})"

    def save(self, *args, **kwargs):
        if not self.report_ref:
            count = WhistleblowerReport.objects.count() + 1
            from django.utils import timezone
            year = timezone.now().year
            self.report_ref = f"WB-{year}-{count:04d}"
        super().save(*args, **kwargs)


class WhistleblowerUpdate(models.Model):
    """
    Investigation updates on a whistleblower report.
    Updated by President or Legal Adviser only.
    Submitter identity never referenced here.
    """
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    report      = models.ForeignKey(
                    WhistleblowerReport,
                    on_delete=models.CASCADE,
                    related_name='updates'
                  )
    updated_by  = models.ForeignKey(
                    User,
                    on_delete=models.SET_NULL,
                    null=True,
                    related_name='wb_updates'
                  )
    old_status  = models.CharField(max_length=20, blank=True)
    new_status  = models.CharField(max_length=20, blank=True)
    note        = models.TextField(blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'whistleblower_updates'
        ordering = ['created_at']

    def __str__(self):
        return f"Update on {self.report.report_ref} by {self.updated_by}"