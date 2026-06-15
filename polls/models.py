import uuid
from django.db import models
from accounts.models import User


class Poll(models.Model):
    """
    ISCOOA-created polls for operator voting.
    Options are Yes/No as per the brief.
    """

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        CLOSED = 'closed', 'Closed'
        DRAFT  = 'draft',  'Draft'

    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    poll_ref        = models.CharField(max_length=30, unique=True, blank=True)
    # e.g. POLL-2026-0001

    question        = models.TextField()
    description     = models.TextField(blank=True)
    # Optional context for the poll question

    status          = models.CharField(
                        max_length=10,
                        choices=Status.choices,
                        default=Status.DRAFT
                      )

    # Who created this poll
    created_by      = models.ForeignKey(
                        User,
                        on_delete=models.SET_NULL,
                        null=True,
                        related_name='created_polls'
                      )

    # Voting window
    opens_at        = models.DateTimeField(null=True, blank=True)
    closes_at       = models.DateTimeField(null=True, blank=True)

    # Target voters — total eligible operators
    target_count    = models.IntegerField(default=0)

    # Live tallies
    yes_count       = models.IntegerField(default=0)
    no_count        = models.IntegerField(default=0)

    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'polls'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.poll_ref} — {self.question[:60]}"

    def save(self, *args, **kwargs):
        if not self.poll_ref:
            count = Poll.objects.count() + 1
            from django.utils import timezone
            year = timezone.now().year
            self.poll_ref = f"POLL-{year}-{count:04d}"
        super().save(*args, **kwargs)

    @property
    def total_votes(self):
        return self.yes_count + self.no_count

    @property
    def yes_percentage(self):
        if self.total_votes == 0:
            return 0
        return round((self.yes_count / self.total_votes) * 100, 1)

    @property
    def no_percentage(self):
        if self.total_votes == 0:
            return 0
        return round((self.no_count / self.total_votes) * 100, 1)

    @property
    def participation_rate(self):
        if self.target_count == 0:
            return 0
        return round((self.total_votes / self.target_count) * 100, 1)


class Vote(models.Model):
    """
    One vote per operator per poll.
    Operators can only vote once.
    """

    class Choice(models.TextChoices):
        YES = 'yes', 'Yes'
        NO  = 'no',  'No'

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    poll        = models.ForeignKey(
                    Poll,
                    on_delete=models.CASCADE,
                    related_name='votes'
                  )
    operator    = models.ForeignKey(
                    User,
                    on_delete=models.CASCADE,
                    related_name='votes'
                  )
    choice      = models.CharField(max_length=5, choices=Choice.choices)
    voted_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'votes'
        # One vote per operator per poll
        unique_together = ['poll', 'operator']

    def __str__(self):
        return f"{self.operator.email} voted {self.choice} on {self.poll.poll_ref}"