from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    LoginView,
    OperatorRegisterView,
    CreatePrivilegedAccountView,
    MeView,
    UserListView,
    ChangePasswordView,
    DeactivateUserView,
    ReactivateUserView,
)

urlpatterns = [
    # ── Public endpoints ────────────────────────────────────────────
    path('login/',          LoginView.as_view(),                name='login'),
    path('refresh/',        TokenRefreshView.as_view(),         name='token_refresh'),
    path('register/',       OperatorRegisterView.as_view(),     name='operator_register'),

    # ── Protected endpoints ─────────────────────────────────────────
    path('create-account/', CreatePrivilegedAccountView.as_view(), name='create_privileged_account'),
    path('me/',             MeView.as_view(),                   name='me'),
    path('change-password/', ChangePasswordView.as_view(),      name='change_password'),

    # ── Super Admin and President only ──────────────────────────────
    path('users/',                          UserListView.as_view(),      name='user_list'),
    path('users/<uuid:pk>/deactivate/',     DeactivateUserView.as_view(), name='deactivate_user'),
    path('users/<uuid:pk>/reactivate/',     ReactivateUserView.as_view(), name='reactivate_user'),
]