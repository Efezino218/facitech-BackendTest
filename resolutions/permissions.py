from rest_framework.permissions import BasePermission


class IsBOTMember(BasePermission):
    """Only BOT members can vote on resolutions."""
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role == 'bot'
        )


class IsAdvisor(BasePermission):
    """Only Advisors can submit advisory notes."""
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role == 'adv'
        )


class IsBOTOrAdvisor(BasePermission):
    """BOT members, Advisors, and President can view resolutions."""
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # BOT members can view
        if request.user.role == 'bot':
            return True
        
        # Advisors can view
        if request.user.role == 'adv':
            return True
        
        # President can view (role='is' and ipos='president')
        if request.user.role == 'is' and request.user.ipos == 'president':
            return True
        
        # Super Admin can view
        if request.user.role == 'sa':
            return True
        
        return False


class CanDraftResolution(BasePermission):
    """
    President, Treasurer, Legal Adviser
    or any BOT member can draft resolutions.
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.role == 'bot':
            return True
        if request.user.role == 'adv':
            return True
        if request.user.role == 'is':
            return request.user.ipos in [
                'president', 'treasurer', 'legal_adviser'
            ]
        if request.user.role == 'sa':
            return True
        return False