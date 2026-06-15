import uuid
from django.db import models
from accounts.models import User


class Publication(models.Model):
    """
    Email blasts, SMS blasts and announcements.
    Created by Secretary General.
    Every broadcast logged with sent date and recipient count.
    """

    class PublicationType(models.TextChoices):
        EMAIL        = 'email',        'Email Blast'
        SMS          = 'sms',          'SMS Blast'
        ANNOUNCEMENT = 'announcement', 'Announcement'

    class TargetGroup(models.TextChoices):
        ALL_OPERATORS  = 'all_operators',  'All Active Operators'
        EXCO_MEMBERS   = 'exco_members',   'Exco Members Only'
        DEFAULTERS     = 'defaulters',     'Defaulters Only'
        BOT_MEMBERS    = 'bot_members',    'Board of Trustees'
        ALL            = 'all',            'Everyone'

    class Status(models.TextChoices):
        DRAFT            = 'draft',            'Draft'
        PENDING_APPROVAL = 'pending_approval', 'Pending Approval'
        SENT             = 'sent',             'Sent'
        SCHEDULED        = 'scheduled',        'Scheduled'
        FAILED           = 'failed',           'Failed'

    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pub_ref         = models.CharField(max_length=30, unique=True, blank=True)
    # e.g. PUB-2026-0001

    pub_type        = models.CharField(max_length=20, choices=PublicationType.choices)
    subject         = models.CharField(max_length=200)
    content         = models.TextField()

    target_group    = models.CharField(
                        max_length=20,
                        choices=TargetGroup.choices,
                        default=TargetGroup.ALL_OPERATORS
                      )

    status          = models.CharField(
                        max_length=20,
                        choices=Status.choices,
                        default=Status.DRAFT
                      )

    # Who created this publication
    created_by      = models.ForeignKey(
                        User,
                        on_delete=models.SET_NULL,
                        null=True,
                        related_name='publications'
                      )

    # Optional attachment file
    attachment      = models.FileField(
                        upload_to='publications/attachments/',
                        null=True, blank=True
                      )

    # Scheduling
    scheduled_for   = models.DateTimeField(null=True, blank=True)
    sent_at         = models.DateTimeField(null=True, blank=True)

    # Stats
    recipient_count = models.IntegerField(default=0)
    open_rate       = models.DecimalField(
                        max_digits=5,
                        decimal_places=2,
                        default=0.00
                      )
    # Open rate percentage for email blasts

    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'publications'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.pub_ref} — {self.subject} ({self.pub_type})"

    def save(self, *args, **kwargs):
        if not self.pub_ref:
            count = Publication.objects.count() + 1
            from django.utils import timezone
            year = timezone.now().year
            self.pub_ref = f"PUB-{year}-{count:04d}"
        super().save(*args, **kwargs)


class Announcement(models.Model):
    """
    Dashboard announcements with priority levels.
    Urgent announcements automatically trigger email and SMS.
    """

    class Priority(models.TextChoices):
        NORMAL = 'normal', 'Normal'
        HIGH   = 'high',   'High'
        URGENT = 'urgent', 'Urgent'

    class Category(models.TextChoices):
        GENERAL_NOTICE = 'general_notice', 'General Notice'
        EMERGENCY      = 'emergency',      'Emergency'
        MEETING        = 'meeting',        'Meeting'
        COMPLIANCE     = 'compliance',     'Compliance'
        AGM            = 'agm',            'AGM'

    class Status(models.TextChoices):
        DRAFT     = 'draft',     'Draft'
        PUBLISHED = 'published', 'Published'
        EXPIRED   = 'expired',   'Expired'

    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ann_ref         = models.CharField(max_length=30, unique=True, blank=True)
    # e.g. ANN-2026-0001

    title           = models.CharField(max_length=200)
    content         = models.TextField()

    priority        = models.CharField(
                        max_length=10,
                        choices=Priority.choices,
                        default=Priority.NORMAL
                      )
    category        = models.CharField(
                        max_length=20,
                        choices=Category.choices,
                        default=Category.GENERAL_NOTICE
                      )

    status          = models.CharField(
                        max_length=10,
                        choices=Status.choices,
                        default=Status.DRAFT
                      )

    # Who created this
    created_by      = models.ForeignKey(
                        User,
                        on_delete=models.SET_NULL,
                        null=True,
                        related_name='announcements'
                      )

    # Dashboard + email/SMS or dashboard only
    send_email      = models.BooleanField(default=False)
    send_sms        = models.BooleanField(default=False)
    # Urgent priority auto-sets both to True

    publish_date    = models.DateTimeField(null=True, blank=True)
    expiry_date     = models.DateTimeField(null=True, blank=True)

    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'announcements'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.ann_ref} — {self.title} ({self.priority})"

    def save(self, *args, **kwargs):
        if not self.ann_ref:
            count = Announcement.objects.count() + 1
            from django.utils import timezone
            year = timezone.now().year
            self.ann_ref = f"ANN-{year}-{count:04d}"
        # Urgent announcements always trigger email and SMS
        if self.priority == self.Priority.URGENT:
            self.send_email = True
            self.send_sms   = True
        super().save(*args, **kwargs)