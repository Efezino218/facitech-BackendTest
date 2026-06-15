from django.urls import path
from .views import (
    MyDisputesView, RaiseDisputeView, MyDisputeDetailView,
    AllDisputesView, DisputeDetailAdminView,
    RespondToDisputeView, DisputeStatsView,
)

urlpatterns = [

    # ── Operator endpoints ──────────────────────────────────────────
    path('my-disputes/',            MyDisputesView.as_view(),       name='my-disputes'),
    path('raise/',                  RaiseDisputeView.as_view(),     name='raise-dispute'),
    path('my-disputes/<uuid:pk>/',  MyDisputeDetailView.as_view(),  name='my-dispute-detail'),

    # ── ISCOOA Executive endpoints ──────────────────────────────────
    path('all/',                    AllDisputesView.as_view(),          name='all-disputes'),
    path('all/<uuid:pk>/',          DisputeDetailAdminView.as_view(),   name='dispute-admin-detail'),
    path('<uuid:pk>/respond/',      RespondToDisputeView.as_view(),     name='dispute-respond'),
    path('stats/',                  DisputeStatsView.as_view(),         name='dispute-stats'),
]