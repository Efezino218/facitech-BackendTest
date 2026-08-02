"""
Management command to expire toilet subscriptions.
Run daily via cron job:
    python manage.py expire_toilet_subscriptions

On Railway/Render:
    0 1 * * * python manage.py expire_toilet_subscriptions
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from toilet.models import ToiletSubscription
from notifications.utils import send_notification


class Command(BaseCommand):
    help = 'Marks expired toilet subscriptions as expired and notifies operators'

    def handle(self, *args, **options):
        now   = timezone.now()
        today = now.date()

        self.stdout.write(
            f'[{now.strftime("%Y-%m-%d %H:%M")}] '
            f'Running toilet subscription expiry check...'
        )

        # Find all active subscriptions that have passed expiry date
        expired_subs = ToiletSubscription.objects.filter(
            status          = ToiletSubscription.Status.ACTIVE,
            expiry_date__lt = today,
        ).select_related('registered_by', 'association')

        expired_count = expired_subs.count()

        if expired_count == 0:
            self.stdout.write(
                self.style.SUCCESS('No subscriptions to expire.')
            )
            return

        # Notify each operator before expiring
        for sub in expired_subs:
            try:
                send_notification(
                    user       = sub.registered_by,
                    category   = 'general',
                    title      = f'Toilet Access Expired — {sub.full_name}',
                    message    = (
                        f'Toilet access for {sub.full_name} '
                        f'(Access Ref: {sub.access_ref}) has expired. '
                        f'The {sub.plan} plan expired on {sub.expiry_date}. '
                        f'Please renew to restore access.'
                    ),
                    related_id = str(sub.id),
                )
            except Exception as e:
                self.stdout.write(
                    f'  Warning: Could not notify {sub.registered_by.email}: {e}'
                )

        # Bulk expire all
        expired_subs.update(status=ToiletSubscription.Status.EXPIRED)

        self.stdout.write(
            self.style.SUCCESS(
                f'Done. Expired {expired_count} toilet subscription(s).'
            )
        )