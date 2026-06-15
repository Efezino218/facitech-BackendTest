import uuid
from django.db import models
from accounts.models import User


class Notification(models.Model):
    """
    Per-user notification feed.
    Every platform event generates a notification record.
    """

    class Category(models.TextChoices):
        BILLS         = 'bills',         'Bills'
        ADVERTS       = 'adverts',       'Adverts'
        DISPUTES      = 'disputes',      'Disputes'
        POLLS         = 'polls',         'Polls'
        PENALTIES     = 'penalties',     'Penalties'
        PAYMENTS      = 'payments',      'Payments'
        KYC           = 'kyc',           'KYC'
        SUBSCRIPTIONS = 'subscriptions', 'Subscriptions'
        TOILET        = 'toilet',        'Toilet'
        GENERAL       = 'general',       'General'

    class Channel(models.TextChoices):
        IN_APP = 'in_app', 'In App'
        EMAIL  = 'email',  'Email'
        SMS    = 'sms',    'SMS'

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user        = models.ForeignKey(
                    User,
                    on_delete=models.CASCADE,
                    related_name='notifications'
                  )

    category    = models.CharField(max_length=20, choices=Category.choices)
    channel     = models.CharField(
                    max_length=10,
                    choices=Channel.choices,
                    default=Channel.IN_APP
                  )
    title       = models.CharField(max_length=200)
    message     = models.TextField()

    # Optional link to the related record
    related_id  = models.CharField(max_length=100, blank=True)
    # e.g. bill UUID or dispute ref

    is_read     = models.BooleanField(default=False)
    read_at     = models.DateTimeField(null=True, blank=True)

    sent_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'notifications'
        ordering = ['-sent_at']

    def __str__(self):
        return f"{self.user.email} — {self.title} ({self.category})"


class NotificationPreference(models.Model):
    """
    Per-user notification preferences.
    Toggle email and SMS per category.
    One record per user.
    """
    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user            = models.OneToOneField(
                        User,
                        on_delete=models.CASCADE,
                        related_name='notification_preferences'
                      )

    # Email toggles per category
    email_bills         = models.BooleanField(default=True)
    email_adverts       = models.BooleanField(default=True)
    email_disputes      = models.BooleanField(default=True)
    email_polls         = models.BooleanField(default=True)
    email_penalties     = models.BooleanField(default=True)
    email_payments      = models.BooleanField(default=True)
    email_kyc           = models.BooleanField(default=True)
    email_subscriptions = models.BooleanField(default=True)
    email_toilet        = models.BooleanField(default=False)
    email_general       = models.BooleanField(default=True)

    # SMS toggles per category
    sms_bills           = models.BooleanField(default=False)
    sms_adverts         = models.BooleanField(default=False)
    sms_disputes        = models.BooleanField(default=True)
    sms_polls           = models.BooleanField(default=False)
    sms_penalties       = models.BooleanField(default=True)
    sms_payments        = models.BooleanField(default=True)
    sms_kyc             = models.BooleanField(default=True)
    sms_subscriptions   = models.BooleanField(default=False)
    sms_toilet          = models.BooleanField(default=False)
    sms_general         = models.BooleanField(default=False)

    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'notification_preferences'

    def __str__(self):
        return f"Preferences for {self.user.email}"