import uuid
from django.db import models
from accounts.models import User


class ExpenseCategory(models.TextChoices):
    FACILITY_MAINTENANCE = 'facility_maintenance', 'Facility Maintenance'
    LEGAL_PROFESSIONAL   = 'legal_professional',   'Legal & Professional Fees'
    EVENT_AGM            = 'event_agm',            'Event/AGM Costs'
    STAFF_WELFARE        = 'staff_welfare',         'Staff Welfare'
    SECURITY             = 'security',             'Security'
    SANITATION           = 'sanitation',           'Sanitation'
    IT_TECHNOLOGY        = 'it_technology',        'IT & Technology'
    OFFICE_SUPPLIES      = 'office_supplies',      'Office Supplies'
    PUBLIC_RELATIONS     = 'public_relations',     'Public Relations'
    EMERGENCY_REPAIRS    = 'emergency_repairs',    'Emergency Repairs'
    CAPITAL_EXPENDITURE  = 'capital_expenditure',  'Capital Expenditure'
    OTHER                = 'other',                'Other'


class ExpenseStatus(models.TextChoices):
    PENDING_TREASURER  = 'pending_treasurer',  'Pending Treasurer Approval'
    PENDING_SECRETARY  = 'pending_secretary',  'Pending Secretary General Approval'
    PENDING_PRESIDENT  = 'pending_president',  'Pending President Approval'
    PENDING_BOT        = 'pending_bot',        'Pending BOT Ratification'
    APPROVED           = 'approved',           'Approved'
    PAID               = 'paid',               'Paid'
    REJECTED           = 'rejected',           'Rejected'


class Expense(models.Model):
    """
    Multi-step expense approval.
    Default workflow: Treasurer → Secretary → President.
    Threshold: ≥ ₦5,000,000 routes additionally to BOT.
    All amounts in kobo.
    """

    # BOT threshold in kobo — ₦5,000,000
    BOT_THRESHOLD = 500000000

    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    expense_ref     = models.CharField(max_length=30, unique=True, blank=True)
    # e.g. EXP-001

    association     = models.ForeignKey(
                        'associations.Association',
                        on_delete=models.CASCADE,
                        related_name='expenses',
                        null=True, blank=True,
                      )

    title           = models.CharField(max_length=200)
    category        = models.CharField(
                        max_length=30,
                        choices=ExpenseCategory.choices
                      )
    amount          = models.BigIntegerField()
    # stored in kobo

    description     = models.TextField()
    evidence        = models.FileField(
                        upload_to='expenses/evidence/',
                        null=True, blank=True
                      )

    status          = models.CharField(
                        max_length=30,
                        choices=ExpenseStatus.choices,
                        default=ExpenseStatus.PENDING_TREASURER
                      )

    # Who raised this expense
    raised_by       = models.ForeignKey(
                        User,
                        on_delete=models.SET_NULL,
                        null=True,
                        related_name='raised_expenses'
                      )
    raised_date     = models.DateField(auto_now_add=True)

    # Whether this expense requires BOT ratification
    requires_bot    = models.BooleanField(default=False)

    # Payment tracking
    paid_at         = models.DateTimeField(null=True, blank=True)
    paid_by         = models.ForeignKey(
                        User,
                        on_delete=models.SET_NULL,
                        null=True, blank=True,
                        related_name='paid_expenses'
                      )
    payment_ref     = models.CharField(max_length=100, blank=True)

    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'expenses'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.expense_ref} — {self.title} ({self.status})"

    def get_bot_threshold(self):
        """Get BOT threshold from association config or use default."""
        try:
            return self.raised_by.association.config.bot_threshold
        except Exception:
            return 500000000  # ₦5,000,000 default

    def save(self, *args, **kwargs):
        if not self.expense_ref:
            count = Expense.objects.count() + 1
            self.expense_ref = f"EXP-{count:03d}"
        # Auto-set BOT requirement based on association config threshold
        self.requires_bot = self.amount >= self.get_bot_threshold()
        super().save(*args, **kwargs)

    @property
    def amount_naira(self):
        return self.amount / 100

    @property
    def requires_bot_ratification(self):
        return self.amount >= self.BOT_THRESHOLD


class ExpenseApprovalStep(models.Model):
    """
    Individual approval steps for an expense.
    One record per step per expense.
    Steps are sequential — each must be approved
    before the next is unlocked.
    """

    class Role(models.TextChoices):
        TREASURER         = 'treasurer',         'Treasurer'
        SECRETARY_GENERAL = 'secretary_general', 'Secretary General'
        PRESIDENT         = 'president',         'President'
        BOT               = 'bot',               'Board of Trustees'

    class StepStatus(models.TextChoices):
        PENDING  = 'pending',  'Pending'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    expense     = models.ForeignKey(
                    Expense,
                    on_delete=models.CASCADE,
                    related_name='approval_steps'
                  )
    step_number = models.IntegerField()
    # 1 = Treasurer, 2 = Secretary, 3 = President, 4 = BOT

    role        = models.CharField(max_length=20, choices=Role.choices)
    actor       = models.ForeignKey(
                    User,
                    on_delete=models.SET_NULL,
                    null=True, blank=True,
                    related_name='expense_approvals'
                  )
    # The actual person who approved/rejected

    status      = models.CharField(
                    max_length=10,
                    choices=StepStatus.choices,
                    default=StepStatus.PENDING
                  )
    note        = models.TextField(blank=True)
    acted_at    = models.DateTimeField(null=True, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'expense_approval_steps'
        ordering = ['step_number']
        unique_together = ['expense', 'step_number']

    def __str__(self):
        return f"{self.expense.expense_ref} — Step {self.step_number} ({self.role}): {self.status}"


def create_approval_steps(expense):
    """
    Create the approval steps for a new expense.
    Default: Treasurer → Secretary → President.
    If amount >= ₦5M: add BOT step.
    """
    steps = [
        (1, ExpenseApprovalStep.Role.TREASURER),
        (2, ExpenseApprovalStep.Role.SECRETARY_GENERAL),
        (3, ExpenseApprovalStep.Role.PRESIDENT),
    ]
    if expense.requires_bot:
        steps.append((4, ExpenseApprovalStep.Role.BOT))

    for step_number, role in steps:
        ExpenseApprovalStep.objects.create(
            expense     = expense,
            step_number = step_number,
            role        = role,
            status      = ExpenseApprovalStep.StepStatus.PENDING,
        )