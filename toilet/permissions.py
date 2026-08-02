from rest_framework.permissions import BasePermission


class IsOperator(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role == 'op'
        )


class IsTreasurer(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role == 'is' and
            request.user.ipos == 'treasurer'
        )


class IsPresident(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role == 'is' and
            request.user.ipos == 'president'
        )


class IsIscooaExec(BasePermission):
    """Any association executive."""
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role == 'is'
        )


class IsTreasurerOrPresident(BasePermission):
    """Treasurer or President — both can view revenue."""
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role == 'is' and
            request.user.ipos in ['treasurer', 'president']
        )