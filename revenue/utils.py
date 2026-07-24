"""
Revenue distribution utility.
Called after every operator payment to split revenue
between the association and Iprolance platform.
"""
from django.db import transaction as db_transaction
from .models import (
    RevenueWallet, RevenueDistribution,
    RevenueWalletType, RevenueSourceType,
)


def get_or_create_association_wallet(association):
    """Get or create the revenue wallet for an association."""
    wallet, _ = RevenueWallet.objects.get_or_create(
        wallet_type = RevenueWalletType.ASSOCIATION,
        association = association,
        defaults    = {
            'name': f'{association.short_name} Revenue',
        }
    )
    return wallet


def get_or_create_platform_wallet():
    """Get or create the Iprolance platform revenue wallet."""
    wallet, _ = RevenueWallet.objects.get_or_create(
        wallet_type = RevenueWalletType.PLATFORM,
        association = None,
        defaults    = {
            'name': 'Iprolance Platform Revenue',
        }
    )
    return wallet


def distribute_revenue(
    association,
    operator,
    total_amount_kobo,
    payment_type,
    source_ref='',
    association_share_pct=None,
    platform_share_pct=None,
    note='',
):
    """
    Split revenue between association and platform after a payment.

    Args:
        association:          Association object
        operator:             User object (who paid)
        total_amount_kobo:    Total payment in kobo
        payment_type:         RevenueDistribution.PaymentType value
        source_ref:           Reference string e.g. payment ref or invoice ID
        association_share_pct: Override percentage (default from config)
        platform_share_pct:   Override percentage (default from config)
        note:                 Optional note

    Returns:
        RevenueDistribution record
    """
    # Get share percentages from association config if not overridden
    if association_share_pct is None or platform_share_pct is None:
        try:
            config = association.config
            association_share_pct = config.association_share
            platform_share_pct    = config.platform_share
        except Exception:
            association_share_pct = 20
            platform_share_pct    = 80

    # Calculate amounts
    association_amount = int(total_amount_kobo * (association_share_pct / 100))
    platform_amount    = int(total_amount_kobo * (platform_share_pct / 100))

    # Handle rounding — ensure amounts add up to total
    # Any rounding remainder goes to association
    remainder = total_amount_kobo - association_amount - platform_amount
    association_amount += remainder

    with db_transaction.atomic():
        # Credit association revenue wallet
        assoc_wallet = get_or_create_association_wallet(association)
        assoc_wallet.credit(
            amount_kobo = association_amount,
            source_type = payment_type,
            source_ref  = source_ref,
            description = (
                f'{payment_type.title()} payment from '
                f'{operator.full_name or operator.email}. '
                f'{association_share_pct}% share.'
            ),
        )

        # Credit platform revenue wallet
        platform_wallet = get_or_create_platform_wallet()
        platform_wallet.credit(
            amount_kobo = platform_amount,
            source_type = payment_type,
            source_ref  = source_ref,
            description = (
                f'{payment_type.title()} payment from '
                f'{operator.full_name or operator.email} '
                f'({association.short_name}). '
                f'{platform_share_pct}% platform share.'
            ),
        )

        # Record the distribution event
        distribution = RevenueDistribution.objects.create(
            association           = association,
            operator              = operator,
            payment_type          = payment_type,
            source_ref            = source_ref,
            total_amount          = total_amount_kobo,
            association_share_pct = association_share_pct,
            platform_share_pct    = platform_share_pct,
            association_amount    = association_amount,
            platform_amount       = platform_amount,
            note                  = note,
        )

    return distribution


def distribute_toilet_revenue(
    association,
    operator,
    total_amount_kobo,
    source_ref='',
    note='',
):
    """
    Toilet revenue goes 100% to association.
    Iprolance takes nothing on toilet subscriptions.
    """
    return distribute_revenue(
        association           = association,
        operator              = operator,
        total_amount_kobo     = total_amount_kobo,
        payment_type          = RevenueDistribution.PaymentType.TOILET,
        source_ref            = source_ref,
        association_share_pct = 100,
        platform_share_pct    = 0,
        note                  = note or '100% toilet revenue to association.',
    )