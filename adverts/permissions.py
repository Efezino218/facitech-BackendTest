from rest_framework.permissions import BasePermission


class IsOperator(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'op'


class IsSecretaryGeneral(BasePermission):
    """Only Secretary General can approve or reject adverts."""
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role == 'is' and
            request.user.ipos == 'secretary_general'
        )


class IsIscooaExec(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'is'