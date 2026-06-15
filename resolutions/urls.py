from django.urls import path
from .views import (
    CreateResolutionView, AllResolutionsView,
    ResolutionDetailView, PublishResolutionView,
    CastResolutionVoteView, FinalizeResolutionView,
    DeferResolutionView,
    SubmitAdvisoryNoteView, MyAdvisoryNotesView,
)

urlpatterns = [

    # ── Resolution management ───────────────────────────────────────
    path('create/',                         CreateResolutionView.as_view(),     name='create-resolution'),
    path('',                                AllResolutionsView.as_view(),       name='all-resolutions'),
    path('<uuid:pk>/',                      ResolutionDetailView.as_view(),     name='resolution-detail'),
    path('<uuid:pk>/publish/',              PublishResolutionView.as_view(),    name='publish-resolution'),
    path('<uuid:pk>/finalize/',             FinalizeResolutionView.as_view(),   name='finalize-resolution'),
    path('<uuid:pk>/defer/',                DeferResolutionView.as_view(),      name='defer-resolution'),

    # ── BOT voting ──────────────────────────────────────────────────
    path('<uuid:pk>/vote/',                 CastResolutionVoteView.as_view(),   name='resolution-vote'),

    # ── Advisor notes ───────────────────────────────────────────────
    path('<uuid:pk>/advisory-note/',        SubmitAdvisoryNoteView.as_view(),   name='advisory-note'),
    path('my-advisory-notes/',             MyAdvisoryNotesView.as_view(),      name='my-advisory-notes'),
]