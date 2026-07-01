import uuid
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


# ─── ROLE CONSTANTS ───────────────────────────────────────────────────────────
class Role(models.TextChoices):
    OPERATOR        = 'op',  'Operator'
    ISCOOA_EXEC     = 'is',  'Association Executive'
    BOARD_OF_TRUSTEE = 'bot', 'Board of Trustees'
    ADVISOR         = 'adv', 'Advisor'
    SUPER_ADMIN     = 'sa',  'Super Admin'


# ISCOOA Executive positions
class ExcoPosition(models.TextChoices):
    PRESIDENT         = 'president',         'President'
    VICE_PRESIDENT    = 'vice_president',    'Vice President'
    SECRETARY_GENERAL = 'secretary_general', 'Secretary General'
    TREASURER         = 'treasurer',         'Treasurer'
    LEGAL_ADVISER     = 'legal_adviser',     'Legal Adviser'
    PRO               = 'pro',               'Public Relations Officer'
    NONE              = 'none',              'None'


# ─── CUSTOM USER MANAGER ──────────────────────────────────────────────────────
class UserManager(BaseUserManager):

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('role', Role.SUPER_ADMIN)
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)


# ─── CUSTOM USER MODEL ────────────────────────────────────────────────────────
class User(AbstractBaseUser, PermissionsMixin):
    """
    Single user table for all 6 roles.
    Role is stored in `role`. ISCOOA exec position in `ipos`.
    Panel permissions stored in `access` (JSONField list).
    """
    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email           = models.EmailField(unique=True)

    # For operators: login can also be shop number e.g. B-11
    username        = models.CharField(max_length=50, unique=True, null=True, blank=True)

    first_name      = models.CharField(max_length=100, blank=True)
    last_name       = models.CharField(max_length=100, blank=True)
    phone           = models.CharField(max_length=20, blank=True)

    # Role — drives which portal the user sees
    role            = models.CharField(max_length=10, choices=Role.choices, default=Role.OPERATOR)

    # ISCOOA Executive position — only relevant when role = 'is'
    ipos            = models.CharField(
                        max_length=30,
                        choices=ExcoPosition.choices,
                        default=ExcoPosition.NONE,
                        blank=True
                      )

    # Panel access list — e.g. ['bills','recon','adverts']
    # President gets 'all'. Others get explicit list.
    access          = models.JSONField(default=list, blank=True)

    # Association this user belongs to
    association     = models.ForeignKey(
                        'associations.Association',
                        on_delete=models.SET_NULL,
                        null=True, blank=True,
                        related_name='users'
                      )

    # Operator-specific
    member_number   = models.CharField(max_length=30, unique=True, null=True, blank=True)
    # e.g. ISCOOA-2026-0047 — assigned after KYC approval

    is_active       = models.BooleanField(default=True)
    is_staff        = models.BooleanField(default=False)

    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD  = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return f"{self.email} ({self.get_role_display()})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def has_panel_access(self, panel: str) -> bool:
        """Check if this user can access a given panel."""
        if self.role == Role.ISCOOA_EXEC and self.ipos == ExcoPosition.PRESIDENT:
            return True  # President sees all 18 panels
        return panel in self.access