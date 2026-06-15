import uuid
from django.db import models
from accounts.models import User


class AuditLog(models.Model):
    """
    Append-only audit log.
    Every significant platform action is recorded here.
    No records are ever deleted or modified.
    Visible to Iprolance Super Admin only.
    """

    class Action(models.TextChoices):
        CREATE   = 'create',   'Create'
        UPDATE   = 'update',   'Update'
        DELETE   = 'delete',   'Delete'
        LOGIN    = 'login',    'Login'
        LOGOUT   = 'logout',   'Logout'
        APPROVE  = 'approve',  'Approve'
        REJECT   = 'reject',   'Reject'
        VERIFY   = 'verify',   'Verify'
        PAY      = 'pay',      'Pay'
        ISSUE    = 'issue',    'Issue'
        LIFT     = 'lift',     'Lift'
        WAIVE    = 'waive',    'Waive'
        SUBMIT   = 'submit',   'Submit'
        VOTE     = 'vote',     'Vote'
        CLOSE    = 'close',    'Close'
        PUBLISH  = 'publish',  'Publish'
        ARCHIVE  = 'archive',  'Archive'
        EXPORT   = 'export',   'Export'
        VIEW     = 'view',     'View'
        OTHER    = 'other',    'Other'

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Who performed the action
    user        = models.ForeignKey(
                    User,
                    on_delete=models.SET_NULL,
                    null=True, blank=True,
                    related_name='audit_logs'
                  )
    user_email  = models.EmailField(blank=True)
    # Stored separately so we keep the record even if user is deleted
    user_role   = models.CharField(max_length=10, blank=True)

    # What they did
    action      = models.CharField(max_length=20, choices=Action.choices)

    # What table/model was affected
    table_name  = models.CharField(max_length=100, blank=True)

    # Which specific record
    record_id   = models.CharField(max_length=100, blank=True)
    record_ref  = models.CharField(max_length=100, blank=True)
    # e.g. KYC-001 or INV-2605-001 — human readable ref

    # What changed
    description = models.TextField(blank=True)
    old_value   = models.JSONField(null=True, blank=True)
    new_value   = models.JSONField(null=True, blank=True)

    # Request metadata
    ip_address  = models.GenericIPAddressField(null=True, blank=True)
    user_agent  = models.TextField(blank=True)

    timestamp   = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'audit_log'
        ordering = ['-timestamp']
        # Prevent any modification of audit records
        # Enforced at the view level — no update endpoints

    def __str__(self):
        return f"{self.user_email} — {self.action} on {self.table_name} ({self.timestamp})"


def log_action(
    user,
    action,
    table_name='',
    record_id='',
    record_ref='',
    description='',
    old_value=None,
    new_value=None,
    request=None,
):
    """
    Central utility to create an audit log entry.
    Called from views after significant actions.

    Usage example:
        from audit.models import log_action
        log_action(
            user        = request.user,
            action      = 'approve',
            table_name  = 'kyc_applications',
            record_id   = str(application.id),
            record_ref  = application.kyc_id,
            description = f'KYC approved for {application.operator.email}',
            request     = request,
        )
    """
    ip_address = None
    user_agent = ''

    if request:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0].strip()
        else:
            ip_address = request.META.get('REMOTE_ADDR')
        user_agent = request.META.get('HTTP_USER_AGENT', '')

    AuditLog.objects.create(
        user        = user,
        user_email  = user.email if user else '',
        user_role   = user.role if user else '',
        action      = action,
        table_name  = table_name,
        record_id   = str(record_id),
        record_ref  = record_ref,
        description = description,
        old_value   = old_value,
        new_value   = new_value,
        ip_address  = ip_address,
        user_agent  = user_agent,
    )