from rest_framework.permissions import BasePermission


class IsOperator(BasePermission):
    """Any operator can submit anonymous reports."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'op'


class IsPresidentOrLegalAdviser(BasePermission):
    """
    Only President or Legal Adviser can view
    and investigate whistleblower reports.
    As per the brief — Section 4.15.
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.role == 'is':
            return request.user.ipos == 'president'
        if request.user.role == 'adv':
            return True
        # Super admin for oversight
        if request.user.role == 'sa':
            return True
        return False