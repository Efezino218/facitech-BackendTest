from django.urls import path
from .views import (
    MyWalletView, TopUpWalletView,
    InitializeTopUpView,
    PaystackCallbackView, PaystackWebhookView,
    WalletTransactionListView, WalletSummaryView,
    AllWalletsView, OperatorWalletDetailView,
)

urlpatterns = [

    # ── Operator endpoints ──────────────────────────────────────────
    path('my-wallet/',      MyWalletView.as_view(),              name='my-wallet'),
    path('summary/',        WalletSummaryView.as_view(),         name='wallet-summary'),
    path('transactions/',   WalletTransactionListView.as_view(), name='wallet-transactions'),

    # ── Top-up — Simulation mode (comment out in production) ───────
    path('top-up/',         TopUpWalletView.as_view(),           name='wallet-top-up-simulation'),

    # ── Top-up — Paystack (real payments) ──────────────────────────
    path('top-up/initialize/',      InitializeTopUpView.as_view(),  name='wallet-topup-initialize'),
    path('paystack/callback/',      PaystackCallbackView.as_view(), name='paystack-callback'),
    path('paystack/webhook/',       PaystackWebhookView.as_view(),  name='paystack-webhook'),

    # ── ISCOOA Executive endpoints ──────────────────────────────────
    path('all/',            AllWalletsView.as_view(),            name='all-wallets'),
    path('all/<uuid:pk>/',  OperatorWalletDetailView.as_view(),  name='wallet-admin-detail'),
]