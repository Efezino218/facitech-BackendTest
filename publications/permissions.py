from rest_framework.permissions import BasePermission


class IsOperator(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'op'


class IsSecretaryGeneral(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role == 'is' and
            request.user.ipos == 'secretary_general'
        )


class IsIscooaExecOrOperator(BasePermission):
    """
    Operators can read announcements.
    Secretary General can create and manage.
    """
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role in ['op', 'is', 'bot', 'adv']
        )