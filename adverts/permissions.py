from rest_framework.permissions import BasePermission


class IsOperator(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role == 'op'
        )


class IsSecretaryGeneral(BasePermission):
    """Secretary General only — can approve and reject adverts."""
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role == 'is' and
            request.user.ipos == 'secretary_general'
        )


class IsSecretaryOrPresident(BasePermission):
    """
    Secretary General can view and manage adverts.
    President can view only.
    Both can see revenue summary.
    """
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role == 'is' and
            request.user.ipos in ['secretary_general', 'president']
        )

class IsIscooaExec(BasePermission):
    """
    Any association executive — read access to advert queue.
    Secretary can act. President can only view.
    """
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role == 'is'
        )


