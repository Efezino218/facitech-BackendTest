from django.urls import path
from .views import (
    ActivePollsView, PollDetailView, CastVoteView,
    CreatePollView, AllPollsView, PollAdminDetailView,
    ClosePollView, PublishPollView,
)

urlpatterns = [

    # ── Operator endpoints ──────────────────────────────────────────
    path('active/',             ActivePollsView.as_view(),      name='active-polls'),
    path('<uuid:pk>/',          PollDetailView.as_view(),       name='poll-detail'),
    path('<uuid:pk>/vote/',     CastVoteView.as_view(),         name='cast-vote'),

    # ── ISCOOA Executive endpoints ──────────────────────────────────
    path('create/',             CreatePollView.as_view(),       name='create-poll'),
    path('all/',                AllPollsView.as_view(),         name='all-polls'),
    path('all/<uuid:pk>/',      PollAdminDetailView.as_view(),  name='poll-admin-detail'),
    path('<uuid:pk>/close/',    ClosePollView.as_view(),        name='close-poll'),
    path('<uuid:pk>/publish/',  PublishPollView.as_view(),      name='publish-poll'),
]