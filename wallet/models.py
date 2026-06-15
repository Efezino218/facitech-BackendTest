import uuid
from django.db import models
from accounts.models import User


class Wallet(models.Model):
    """
    One wallet per operator.
    Powered by Cool Microfinance Bank.
    Balance stored in kobo (integer).
    """
    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    operator        = models.OneToOneField(
                        User,
                        on_delete=models.CASCADE,
                        related_name='wallet'
                      )

    # Balance in kobo
    balance         = models.BigIntegerField(default=0)

    # Cool MFB account details
    coolmfb_account_number = models.CharField(max_length=20, blank=True)
    coolmfb_account_name   = models.CharField(max_length=200, blank=True)

    is_active       = models.BooleanField(default=True)
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'wallets'

    def __str__(self):
        return f"{self.operator.email} — ₦{self.balance_naira}"

    @property
    def balance_naira(self):
        return self.balance / 100

    def credit(self, amount_kobo, description='', method='', ref=''):
        """
        Credit the wallet by amount_kobo.
        Creates a transaction record automatically.
        """
        self.balance += amount_kobo
        self.save()
        return WalletTransaction.objects.create(
            wallet      = self,
            operator    = self.operator,
            type        = WalletTransaction.Type.CREDIT,
            amount      = amount_kobo,
            description = description,
            method      = method,
            reference   = ref,
            confirmed   = True,
        )

    def debit(self, amount_kobo, description='', method='', ref=''):
        """
        Debit the wallet by amount_kobo.
        Raises ValueError if insufficient balance.
        """
        if self.balance < amount_kobo:
            raise ValueError(
                f"Insufficient wallet balance. "
                f"Available: ₦{self.balance_naira}, "
                f"Required: ₦{amount_kobo / 100}"
            )
        self.balance -= amount_kobo
        self.save()
        return WalletTransaction.objects.create(
            wallet      = self,
            operator    = self.operator,
            type        = WalletTransaction.Type.DEBIT,
            amount      = amount_kobo,
            description = description,
            method      = method,
            reference   = ref,
            confirmed   = True,
        )


class WalletTransaction(models.Model):
    """
    Ledger of all wallet transactions.
    Every credit and debit is recorded here.
    """

    class Type(models.TextChoices):
        CREDIT = 'credit', 'Credit'
        DEBIT  = 'debit',  'Debit'

    class Method(models.TextChoices):
        PAYSTACK      = 'paystack',      'Paystack Card'
        BANK_TRANSFER = 'bank_transfer', 'Bank Transfer to Cool MFB'
        USSD          = 'ussd',          'USSD *737#'
        WALLET        = 'wallet',        'Cool MFB Wallet'
        SYSTEM        = 'system',        'System'

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wallet      = models.ForeignKey(
                    Wallet,
                    on_delete=models.CASCADE,
                    related_name='transactions'
                  )
    operator    = models.ForeignKey(
                    User,
                    on_delete=models.CASCADE,
                    related_name='wallet_transactions'
                  )

    type        = models.CharField(max_length=10, choices=Type.choices)
    amount      = models.BigIntegerField()
    # stored in kobo

    description = models.CharField(max_length=255, blank=True)
    method      = models.CharField(max_length=20, choices=Method.choices, blank=True)
    reference   = models.CharField(max_length=100, blank=True)
    # Cool MFB transaction reference

    confirmed   = models.BooleanField(default=False)
    confirmed_by = models.ForeignKey(
                    User,
                    on_delete=models.SET_NULL,
                    null=True, blank=True,
                    related_name='confirmed_transactions'
                  )

    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'wallet_transactions'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.type} ₦{self.amount / 100} — {self.operator.email}"

    @property
    def amount_naira(self):
        return self.amount / 100