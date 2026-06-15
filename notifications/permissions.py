from rest_framework.permissions import BasePermission


class IsAuthenticated(BasePermission):
    """Any authenticated user can access their own notifications."""
    def has_permission(self, request, view):
        return request.user.is_authenticated