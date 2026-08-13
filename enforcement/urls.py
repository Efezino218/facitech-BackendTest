from django.urls import path
from .views import (
    MyPenaltiesView, MyShutdownsView, IssuePenaltyView, AllPenaltiesView,
    PenaltyDetailAdminView, WaivePenaltyView,
    IssueShutdownView, AllShutdownsView, LiftShutdownView,
    RespondToPenaltyView, PayPenaltyFineView,
    RespondToShutdownView, AcknowledgePenaltyResponseView, EnforcementStatsView,
    ShutdownDetailAdminView,
)

urlpatterns = [

    # ── Operator endpoints ──────────────────────────────────────────
    path('my-penalties/',
         MyPenaltiesView.as_view(),
         name='my-penalties'),
    path('my-penalties/<uuid:pk>/respond/',
         RespondToPenaltyView.as_view(),
         name='respond-penalty'),
    path('my-penalties/<uuid:pk>/pay-fine/',
         PayPenaltyFineView.as_view(),
         name='pay-penalty-fine'),
    path('my-shutdowns/',
         MyShutdownsView.as_view(),
         name='my-shutdowns'),
    path('my-shutdowns/<uuid:pk>/respond/',
         RespondToShutdownView.as_view(),
         name='respond-shutdown'),

    # ── ISCOOA Executive endpoints ──────────────────────────────────
    path('issue-penalty/',
         IssuePenaltyView.as_view(),
         name='issue-penalty'),
    path('all-penalties/',
         AllPenaltiesView.as_view(),
         name='all-penalties'),
    path('all-penalties/<uuid:pk>/',
         PenaltyDetailAdminView.as_view(),
         name='penalty-detail'),
    path('all-penalties/<uuid:pk>/waive/',
         WaivePenaltyView.as_view(),
         name='waive-penalty'),
    path('all-penalties/<uuid:pk>/acknowledge-response/',
         AcknowledgePenaltyResponseView.as_view(),
         name='acknowledge-penalty-response'),
    path('issue-shutdown/',
         IssueShutdownView.as_view(),
         name='issue-shutdown'),
    path('all-shutdowns/',
         AllShutdownsView.as_view(),
         name='all-shutdowns'),
    path('all-shutdowns/<uuid:pk>/lift/',
         LiftShutdownView.as_view(),
         name='lift-shutdown'),
         
     path('all-shutdowns/<uuid:pk>/', ShutdownDetailAdminView.as_view(), name='shutdown-detail'),

                 # ── Stats ───────────────────────────────────────────────────────
    path('stats/',                      EnforcementStatsView.as_view(),                 name='enforcement-stats'),
]