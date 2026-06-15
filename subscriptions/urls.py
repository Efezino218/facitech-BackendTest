from django.urls import path
from .views import (
    MySubscriptionView, PaySubscriptionView,
    AllSubscriptionsView, SubscriptionDetailAdminView,
    CommissionSummaryView,
)

urlpatterns = [

    # ── Operator endpoints ──────────────────────────────────────────
    path('my-subscription/', MySubscriptionView.as_view(),  name='my-subscription'),
    path('pay/',             PaySubscriptionView.as_view(), name='pay-subscription'),

    # ── ISCOOA Treasurer endpoints ──────────────────────────────────
    path('all/',             AllSubscriptionsView.as_view(),         name='all-subscriptions'),
    path('all/<uuid:pk>/',   SubscriptionDetailAdminView.as_view(),  name='subscription-admin-detail'),
    path('commission-summary/', CommissionSummaryView.as_view(),     name='commission-summary'),
]