from django.urls import path
from .views import (
    AssociationRevenueDashboardView,
    AssociationRevenueTransactionsView,
    AssociationRevenueDistributionsView,
    PlatformRevenueDashboardView,
    PlatformRevenueTransactionsView,
    AllDistributionsView,
    RevenueWalletListView,
    RequestWithdrawalView,
    AssociationWithdrawalListView,
    AssociationWithdrawalDetailView,
    ApproveWithdrawalView,
    RejectWithdrawalView,
    AllWithdrawalsAdminView,
    ProcessWithdrawalView,
)

urlpatterns = [

    # ── Association Treasurer and President ─────────────────────────
    path('association/dashboard/',      AssociationRevenueDashboardView.as_view(),     name='assoc-revenue-dashboard'),
    path('association/transactions/',   AssociationRevenueTransactionsView.as_view(),  name='assoc-revenue-transactions'),
    path('association/distributions/',  AssociationRevenueDistributionsView.as_view(), name='assoc-revenue-distributions'),

    # ── Withdrawal — Treasurer ──────────────────────────────────────
    path('withdrawals/request/',        RequestWithdrawalView.as_view(),               name='request-withdrawal'),
    path('withdrawals/',                AssociationWithdrawalListView.as_view(),       name='withdrawal-list'),
    path('withdrawals/<uuid:pk>/',      AssociationWithdrawalDetailView.as_view(),     name='withdrawal-detail'),

    # ── Withdrawal — President ──────────────────────────────────────
    path('withdrawals/<uuid:pk>/approve/', ApproveWithdrawalView.as_view(),            name='approve-withdrawal'),
    path('withdrawals/<uuid:pk>/reject/',  RejectWithdrawalView.as_view(),             name='reject-withdrawal'),

    # ── Iprolance Super Admin ───────────────────────────────────────
    path('platform/dashboard/',             PlatformRevenueDashboardView.as_view(),    name='platform-revenue-dashboard'),
    path('platform/transactions/',          PlatformRevenueTransactionsView.as_view(), name='platform-revenue-transactions'),
    path('platform/distributions/',         AllDistributionsView.as_view(),            name='all-distributions'),
    path('wallets/',                        RevenueWalletListView.as_view(),           name='revenue-wallets'),
    path('admin/withdrawals/',              AllWithdrawalsAdminView.as_view(),         name='all-withdrawals-admin'),
    path('admin/withdrawals/<uuid:pk>/process/', ProcessWithdrawalView.as_view(),      name='process-withdrawal'),
]