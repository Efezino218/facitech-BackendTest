from .models import Notification


def get_platform_name(user):
    """
    Get the association name for notification messages.
    Falls back to 'ISCOOA Facitech' if no association found.
    """
    try:
        return user.association.name
    except Exception:
        return 'ISCOOA Facitech'


def send_notification(user, category, title, message, related_id='', channel='in_app'):
    """
    Central utility to create a notification for a user.
    Called by other modules when events occur.
    """
    Notification.objects.create(
        user       = user,
        category   = category,
        channel    = channel,
        title      = title,
        message    = message,
        related_id = related_id,
    )


def send_bulk_notification(users, category, title, message, related_id='', channel='in_app'):
    """
    Send the same notification to multiple users at once.
    Uses bulk_create for efficiency.
    """
    notifications = [
        Notification(
            user       = user,
            category   = category,
            channel    = channel,
            title      = title,
            message    = message,
            related_id = related_id,
        )
        for user in users
    ]
    Notification.objects.bulk_create(notifications)