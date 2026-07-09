"""
Management command to check and update overdue subscriptions.
Run daily via cron job:
    python manage.py check_overdue_subscriptions

On Railway/Render set up a cron job to run this every day at midnight.
Example cron: 0 0 * * * python manage.py check_overdue_subscriptions
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from subscriptions.models import Subscription, SubscriptionPayment
from notifications.utils import send_notification
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Checks subscriptions and marks overdue/suspended as appropriate'

    def handle(self, *args, **options):
        now = timezone.now()
        today = now.date()

        self.stdout.write(
            f'[{now.strftime("%Y-%m-%d %H:%M")}] '
            f'Running subscription overdue check...'
        )

        # ── Step 1: Mark ACTIVE subscriptions as OVERDUE ──────────────
        # Find active subscriptions where renewal_date has passed
        newly_overdue = Subscription.objects.filter(
            status       = Subscription.Status.ACTIVE,
            renewal_date__lt = today,
        )

        overdue_count = 0
        for subscription in newly_overdue:
            subscription.status       = Subscription.Status.OVERDUE
            subscription.overdue_since = now
            subscription.save()

            # Notify the operator
            try:
                assoc_name = subscription.operator.association.name
            except Exception:
                assoc_name = 'ISCOOA'

            send_notification(
                user     = subscription.operator,
                category = 'subscriptions',
                title    = 'Subscription Payment Overdue',
                message  = (
                    f'Your {assoc_name} Facitech subscription payment is overdue. '
                    f'Monthly fee: ₦{subscription.monthly_fee_naira:,.2f} '
                    f'for {subscription.shop_count} shop(s). '
                    f'Please pay immediately to avoid suspension.'
                ),
            )
            overdue_count += 1
            self.stdout.write(
                f'  → Marked OVERDUE: {subscription.operator.email}'
            )

        # ── Step 2: Send reminders for existing OVERDUE subscriptions ──
        # Remind operators who are already overdue but not yet suspended
        existing_overdue = Subscription.objects.filter(
            status = Subscription.Status.OVERDUE,
        )

        reminder_count = 0
        for subscription in existing_overdue:
            # Only remind once per day — skip if reminded today
            if subscription.last_reminded_at:
                last_reminded_date = subscription.last_reminded_at.date()
                if last_reminded_date == today:
                    continue

            try:
                assoc_name = subscription.operator.association.name
            except Exception:
                assoc_name = 'ISCOOA'

            days_overdue = (today - subscription.renewal_date).days if subscription.renewal_date else 0

            send_notification(
                user     = subscription.operator,
                category = 'subscriptions',
                title    = f'Subscription Reminder — {days_overdue} day(s) overdue',
                message  = (
                    f'Your {assoc_name} Facitech subscription is {days_overdue} day(s) overdue. '
                    f'Amount due: ₦{subscription.monthly_fee_naira:,.2f}. '
                    f'Your account will be suspended after {subscription.grace_period_days} days '
                    f'of non-payment.'
                ),
            )
            subscription.last_reminded_at = now
            subscription.save(update_fields=['last_reminded_at'])
            reminder_count += 1

        # ── Step 3: Suspend after grace period ────────────────────────
        # Find overdue subscriptions that have exceeded the grace period
        newly_suspended = Subscription.objects.filter(
            status = Subscription.Status.OVERDUE,
        )

        suspended_count = 0
        for subscription in newly_suspended:
            if not subscription.overdue_since:
                continue

            days_since_overdue = (now - subscription.overdue_since).days
            if days_since_overdue >= subscription.grace_period_days:
                subscription.status           = Subscription.Status.SUSPENDED
                subscription.suspended_since  = now
                subscription.suspended_reason = (
                    f'Automatically suspended after {days_since_overdue} days '
                    f'of non-payment. Renewal was due on {subscription.renewal_date}.'
                )
                subscription.save()

                try:
                    assoc_name = subscription.operator.association.name
                except Exception:
                    assoc_name = 'ISCOOA'

                send_notification(
                    user     = subscription.operator,
                    category = 'subscriptions',
                    title    = 'Account Suspended — Subscription Unpaid',
                    message  = (
                        f'Your {assoc_name} Facitech account has been suspended '
                        f'due to non-payment of subscription fees. '
                        f'Amount due: ₦{subscription.monthly_fee_naira:,.2f}. '
                        f'Please contact {assoc_name} to reinstate your account.'
                    ),
                )
                suspended_count += 1
                self.stdout.write(
                    f'  → SUSPENDED: {subscription.operator.email} '
                    f'({days_since_overdue} days overdue)'
                )

        # ── Summary ───────────────────────────────────────────────────
        self.stdout.write(
            self.style.SUCCESS(
                f'\nDone. '
                f'Newly overdue: {overdue_count} | '
                f'Reminders sent: {reminder_count} | '
                f'Newly suspended: {suspended_count}'
            )
        )