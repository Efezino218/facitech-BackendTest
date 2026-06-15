from rest_framework.permissions import BasePermission


class IsSuperAdmin(BasePermission):
    """
    Only Iprolance Super Admin can view the audit log.
    """
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role == 'sa'
        )


class IsPresidentOrSuperAdmin(BasePermission):
    """
    President or Super Admin can view audit logs.
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.role == 'sa':
            return True
        if request.user.role == 'is' and request.user.ipos == 'president':
            return True
        return False