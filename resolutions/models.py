import uuid
from django.db import models
from accounts.models import User


class Resolution(models.Model):
    """
    BOT resolutions.
    Drafted by President, Treasurer, Legal Adviser
    or any BOT member.
    Advisors review and add notes — no vote.
    BOT votes: Yea / Nay / Abstain.
    Simple majority required to pass.
    """

    class Status(models.TextChoices):
        DRAFT    = 'draft',    'Draft'
        PENDING  = 'pending',  'Pending Vote'
        PASSED   = 'passed',   'Passed'
        REJECTED = 'rejected', 'Rejected'
        DEFERRED = 'deferred', 'Deferred'

    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    res_ref         = models.CharField(max_length=30, unique=True, blank=True)
    # e.g. RES-001

    association     = models.ForeignKey(
                        'associations.Association',
                        on_delete=models.CASCADE,
                        related_name='resolutions',
                        null=True, blank=True,
                      )

    title           = models.CharField(max_length=200)
    full_text       = models.TextField()
    # Full resolution text

    status          = models.CharField(
                        max_length=10,
                        choices=Status.choices,
                        default=Status.DRAFT
                      )

    # Who proposed this resolution
    proposed_by     = models.ForeignKey(
                        User,
                        on_delete=models.SET_NULL,
                        null=True,
                        related_name='proposed_resolutions'
                      )
    proposed_date   = models.DateField(null=True, blank=True)

    # Vote tallies
    yea_count       = models.IntegerField(default=0)
    nay_count       = models.IntegerField(default=0)
    abstain_count   = models.IntegerField(default=0)

    # Once passed
    ratified_date   = models.DateTimeField(null=True, blank=True)
    signatories     = models.JSONField(default=list, blank=True)
    # List of BOT member names who signed

    # BOT resolution note for expenses etc
    resolution_note = models.TextField(blank=True)

    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'resolutions'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.res_ref} — {self.title} ({self.status})"

    def save(self, *args, **kwargs):
        if not self.res_ref:
            count = Resolution.objects.count() + 1
            self.res_ref = f"RES-{count:03d}"
        super().save(*args, **kwargs)

    @property
    def total_votes(self):
        return self.yea_count + self.nay_count + self.abstain_count

    @property
    def is_passed(self):
        if self.total_votes == 0:
            return False
        return self.yea_count > self.nay_count


class ResolutionVote(models.Model):
    """
    Individual BOT member votes on a resolution.
    One vote per BOT member per resolution.
    """

    class Choice(models.TextChoices):
        YEA     = 'yea',     'Yea'
        NAY     = 'nay',     'Nay'
        ABSTAIN = 'abstain', 'Abstain'

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    resolution  = models.ForeignKey(
                    Resolution,
                    on_delete=models.CASCADE,
                    related_name='votes'
                  )
    bot_member  = models.ForeignKey(
                    User,
                    on_delete=models.CASCADE,
                    related_name='resolution_votes'
                  )
    choice      = models.CharField(max_length=10, choices=Choice.choices)
    note        = models.TextField(blank=True)
    voted_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'resolution_votes'
        unique_together = ['resolution', 'bot_member']

    def __str__(self):
        return f"{self.bot_member.email} voted {self.choice} on {self.resolution.res_ref}"


class AdvisoryNote(models.Model):
    """
    Advisory notes added by Advisors on resolutions.
    Counsel only — no voting power.
    Visible to BOT and President.
    """
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    resolution  = models.ForeignKey(
                    Resolution,
                    on_delete=models.CASCADE,
                    related_name='advisory_notes'
                  )
    advisor     = models.ForeignKey(
                    User,
                    on_delete=models.CASCADE,
                    related_name='advisory_notes'
                  )
    note        = models.TextField()
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'advisory_notes'
        ordering = ['submitted_at']
        # One note per advisor per resolution
        unique_together = ['resolution', 'advisor']

    def __str__(self):
        return f"Note by {self.advisor.email} on {self.resolution.res_ref}"