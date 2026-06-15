from django.urls import path
from .views import (
    MyWalletView, TopUpWalletView,
    WalletTransactionListView, WalletSummaryView,
    AllWalletsView, OperatorWalletDetailView,
)

urlpatterns = [

    # ── Operator endpoints ──────────────────────────────────────────
    path('my-wallet/',      MyWalletView.as_view(),              name='my-wallet'),
    path('top-up/',         TopUpWalletView.as_view(),           name='wallet-top-up'),
    path('transactions/',   WalletTransactionListView.as_view(), name='wallet-transactions'),
    path('summary/',        WalletSummaryView.as_view(),         name='wallet-summary'),

    # ── ISCOOA Executive endpoints ──────────────────────────────────
    path('all/',            AllWalletsView.as_view(),            name='all-wallets'),
    path('all/<uuid:pk>/',  OperatorWalletDetailView.as_view(),  name='wallet-admin-detail'),
]