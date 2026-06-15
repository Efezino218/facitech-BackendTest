from django.urls import path
from .views import (
    ToiletPricingView, RegisterToiletView,
    MyToiletSubscriptionsView, RenewToiletView,
    AllToiletSubscriptionsView, ToiletRevenueSummaryView,
    UpdateToiletPricingView,
)

urlpatterns = [

    # ── Operator endpoints ──────────────────────────────────────────
    path('pricing/',            ToiletPricingView.as_view(),          name='toilet-pricing'),
    path('register/',           RegisterToiletView.as_view(),         name='toilet-register'),
    path('my-subscriptions/',   MyToiletSubscriptionsView.as_view(),  name='my-toilet-subscriptions'),
    path('<uuid:pk>/renew/',    RenewToiletView.as_view(),            name='toilet-renew'),

    # ── ISCOOA Treasurer endpoints ──────────────────────────────────
    path('all/',                AllToiletSubscriptionsView.as_view(), name='all-toilet-subscriptions'),
    path('revenue-summary/',    ToiletRevenueSummaryView.as_view(),   name='toilet-revenue-summary'),
    path('pricing/update/',     UpdateToiletPricingView.as_view(),    name='update-toilet-pricing'),
]