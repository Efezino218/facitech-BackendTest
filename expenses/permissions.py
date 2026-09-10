from rest_framework.permissions import BasePermission


class IsIscooaExec(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role == 'is'
        )


class IsTreasurer(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role == 'is' and
            request.user.ipos == 'treasurer'
        )


class IsBOTMember(BasePermission):
    """Any BOT member — can VIEW but not act."""
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role == 'bot'
        )


class IsBOTChairman(BasePermission):
    """
    BOT Chairman only — can ratify, defer or reject.
    Uses ipos field to identify chairman.
    """
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role == 'bot' and
            request.user.ipos == 'chairman'
        )