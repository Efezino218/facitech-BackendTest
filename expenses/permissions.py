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


class IsSecretaryGeneral(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role == 'is' and
            request.user.ipos == 'secretary_general'
        )


class IsPresident(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role == 'is' and
            request.user.ipos == 'president'
        )


class IsBOTMember(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role == 'bot'
        )


class IsTreasurerOrPresident(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role == 'is' and
            request.user.ipos in ['treasurer', 'president']
        )