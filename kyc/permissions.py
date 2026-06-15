from rest_framework.permissions import BasePermission


class IsOperator(BasePermission):
    """Only operators can access this view."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'op'


class IsIscooaExec(BasePermission):
    """Only ISCOOA executives can access this view."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'is'


class IsIscooaExecOrSuperAdmin(BasePermission):
    """ISCOOA executives or super admin."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['is', 'sa']