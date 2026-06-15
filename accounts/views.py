from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import User, Role
from .serializers import (
    UserSerializer,
    OperatorRegisterSerializer,
    PrivilegedAccountCreateSerializer,
    CustomTokenObtainPairSerializer,
    ChangePasswordSerializer,
    DeactivateAccountSerializer,
)


@extend_schema(tags=['Auth'])
class LoginView(TokenObtainPairView):
    """
    POST /api/v1/auth/login/
    Returns access + refresh tokens with user data.
    Blocks inactive accounts.
    Rate limited to 10 attempts per minute per IP.
    Account locked after 5 failed attempts (django-axes).
    """
    serializer_class   = CustomTokenObtainPairSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        # Rate limit login attempts
        from django_ratelimit.core import is_ratelimited
        limited = is_ratelimited(
            request   = request,
            group     = 'login',
            key       = 'ip',
            rate      = '10/m',
            method    = 'POST',
            increment = True,
        )
        if limited:
            return Response(
                {
                    'detail': (
                        'Too many login attempts. '
                        'Please wait 1 minute before trying again.'
                    )
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        return super().post(request, *args, **kwargs)


@extend_schema(tags=['Auth'])
class OperatorRegisterView(generics.CreateAPIView):
    """
    POST /api/v1/auth/register/
    PUBLIC endpoint — operators only.
    Rate limited to 5 registrations per hour per IP.
    """
    serializer_class   = OperatorRegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        # Rate limit registrations
        from django_ratelimit.core import is_ratelimited
        limited = is_ratelimited(
            request   = request,
            group     = 'register',
            key       = 'ip',
            rate      = '5/h',
            method    = 'POST',
            increment = True,
        )
        if limited:
            return Response(
                {
                    'detail': (
                        'Too many registration attempts from this IP address. '
                        'Please try again later.'
                    )
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {
                'detail':    'Operator account created successfully. Please log in and complete your KYC.',
                'email':     user.email,
                'role':      user.role,
                'next_step': 'Complete KYC at /api/v1/kyc/start/',
            },
            status=status.HTTP_201_CREATED
        )


@extend_schema(tags=['Auth'])
class CreatePrivilegedAccountView(generics.CreateAPIView):
    """
    POST /api/v1/auth/create-account/
    PROTECTED — President or Super Admin only.
    Creates Exco, BOT, Advisor or Super Admin accounts.
    Operators must use the public register endpoint.
    """
    serializer_class = PrivilegedAccountCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        # Only President or Super Admin can create privileged accounts
        user = request.user
        allowed = (
            user.role == 'sa' or
            (user.role == 'is' and user.ipos == 'president')
        )
        if not allowed:
            return Response(
                {
                    'detail': 'Only the President or Super Admin can create privileged accounts.'
                },
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_user = serializer.save()

        return Response(
            {
                'detail':     f'{new_user.get_role_display()} account created successfully.',
                'email':      new_user.email,
                'role':       new_user.role,
                'ipos':       new_user.ipos,
                'created_by': request.user.email,
            },
            status=status.HTTP_201_CREATED
        )


@extend_schema(tags=['Auth'])
class MeView(APIView):
    """
    GET /api/v1/auth/me/
    Returns the currently logged-in user profile.
    Also returns KYC status for operators.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        data = serializer.data

        # Add KYC status for operators
        if request.user.role == Role.OPERATOR:
            try:
                kyc = request.user.kyc_application
                data['kyc_status']  = kyc.status
                data['kyc_id']      = kyc.kyc_id
                data['member_number'] = kyc.member_number
            except Exception:
                data['kyc_status']  = 'not_started'
                data['kyc_id']      = None

        return Response(data)


@extend_schema(tags=['Auth'])
class UserListView(generics.ListAPIView):
    """
    GET /api/v1/auth/users/
    Super Admin only — lists all users.
    Filter by ?role=op|is|bot|adv|sa
    Filter by ?is_active=true|false
    """
    serializer_class   = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role != 'sa':
            return User.objects.none()

        qs = User.objects.all().order_by('-created_at')
        role = self.request.query_params.get('role')
        if role:
            qs = qs.filter(role=role)
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == 'true')
        return qs


@extend_schema(tags=['Auth'])
class ChangePasswordView(APIView):
    """
    POST /api/v1/auth/change-password/
    Any authenticated user can change their own password.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(
            data    = request.data,
            context = {'request': request}
        )
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        request.user.set_password(
            serializer.validated_data['new_password']
        )
        request.user.save()
        return Response({
            'detail': 'Password changed successfully. Please login again with your new password.'
        })


@extend_schema(tags=['Auth'])
class DeactivateUserView(APIView):
    """
    POST /api/v1/auth/users/<id>/deactivate/
    President or Super Admin deactivates a user account.
    Deactivated accounts cannot login.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        # Only President or Super Admin
        user = request.user
        allowed = (
            user.role == 'sa' or
            (user.role == 'is' and user.ipos == 'president')
        )
        if not allowed:
            return Response(
                {'detail': 'Only the President or Super Admin can deactivate accounts.'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            target_user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response(
                {'detail': 'User not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Cannot deactivate yourself
        if target_user == request.user:
            return Response(
                {'detail': 'You cannot deactivate your own account.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Cannot deactivate Super Admin
        if target_user.role == 'sa':
            return Response(
                {'detail': 'Super Admin accounts cannot be deactivated via the API.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = DeactivateAccountSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        target_user.is_active = False
        target_user.save()

        return Response({
            'detail':           f'Account {target_user.email} has been deactivated.',
            'deactivated_by':   request.user.email,
            'reason':           serializer.validated_data['reason'],
        })


@extend_schema(tags=['Auth'])
class ReactivateUserView(APIView):
    """
    POST /api/v1/auth/users/<id>/reactivate/
    President or Super Admin reactivates a deactivated account.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        user = request.user
        allowed = (
            user.role == 'sa' or
            (user.role == 'is' and user.ipos == 'president')
        )
        if not allowed:
            return Response(
                {'detail': 'Only the President or Super Admin can reactivate accounts.'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            target_user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response(
                {'detail': 'User not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        target_user.is_active = True
        target_user.save()

        return Response({
            'detail':         f'Account {target_user.email} has been reactivated.',
            'reactivated_by': request.user.email,
        })