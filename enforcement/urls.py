from django.urls import path
from .views import (
    MyPenaltiesView, MyPenaltyDetailView, MyShutdownsView,
    AllPenaltiesView, IssuePenaltyView, PenaltyDetailAdminView,
    WaivePenaltyView,
    AllShutdownsView, IssueShutdownView, LiftShutdownView,
    EnforcementStatsView,
)

urlpatterns = [

    # ── Operator endpoints ──────────────────────────────────────────
    path('my-penalties/',               MyPenaltiesView.as_view(),          name='my-penalties'),
    path('my-penalties/<uuid:pk>/',     MyPenaltyDetailView.as_view(),      name='my-penalty-detail'),
    path('my-shutdowns/',               MyShutdownsView.as_view(),          name='my-shutdowns'),

    # ── ISCOOA Executive penalty endpoints ─────────────────────────
    path('all-penalties/',              AllPenaltiesView.as_view(),         name='all-penalties'),
    path('issue-penalty/',              IssuePenaltyView.as_view(),         name='issue-penalty'),
    path('all-penalties/<uuid:pk>/',    PenaltyDetailAdminView.as_view(),   name='penalty-admin-detail'),
    path('penalties/<uuid:pk>/waive/',  WaivePenaltyView.as_view(),         name='waive-penalty'),

    # ── ISCOOA Executive shutdown endpoints ────────────────────────
    path('all-shutdowns/',              AllShutdownsView.as_view(),         name='all-shutdowns'),
    path('issue-shutdown/',             IssueShutdownView.as_view(),        name='issue-shutdown'),
    path('shutdowns/<uuid:pk>/lift/',   LiftShutdownView.as_view(),         name='lift-shutdown'),

    # ── Stats ───────────────────────────────────────────────────────
    path('stats/',                      EnforcementStatsView.as_view(),     name='enforcement-stats'),
]