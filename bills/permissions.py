from rest_framework.permissions import BasePermission


class IsOperator(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'op'


class IsIscooaExec(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'is'


class IsTreasurer(BasePermission):
    """Only the ISCOOA Treasurer can raise and verify bills."""
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role == 'is' and
            request.user.ipos == 'treasurer'
        )


class IsTreasurerOrSecretary(BasePermission):
    """Treasurer or Secretary General can verify bills."""
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role == 'is' and
            request.user.ipos in ['treasurer', 'secretary_general']
        )