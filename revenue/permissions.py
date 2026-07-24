from rest_framework.permissions import BasePermission


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


class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role == 'sa'
        )


class IsTreasurerOrPresident(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role == 'is' and
            request.user.ipos in ['treasurer', 'president']
        )