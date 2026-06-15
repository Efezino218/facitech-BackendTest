from rest_framework.permissions import BasePermission


class IsOperator(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'op'


class IsIscooaExec(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'is'


class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'sa'