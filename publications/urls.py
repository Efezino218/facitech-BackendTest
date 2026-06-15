from django.urls import path
from .views import (
    CreatePublicationView, AllPublicationsView,
    PublicationDetailView, SendPublicationView,
    CreateAnnouncementView, AllAnnouncementsView,
    AnnouncementDetailView, PublicationStatsView,
)

urlpatterns = [

    # ── Secretary General publication endpoints ─────────────────────
    path('create/',                         CreatePublicationView.as_view(),    name='create-publication'),
    path('',                                AllPublicationsView.as_view(),      name='all-publications'),
    path('<uuid:pk>/',                      PublicationDetailView.as_view(),    name='publication-detail'),
    path('<uuid:pk>/send/',                 SendPublicationView.as_view(),      name='send-publication'),
    path('stats/',                          PublicationStatsView.as_view(),     name='publication-stats'),

    # ── Announcement endpoints ──────────────────────────────────────
    path('announcements/create/',           CreateAnnouncementView.as_view(),   name='create-announcement'),
    path('announcements/',                  AllAnnouncementsView.as_view(),     name='all-announcements'),
    path('announcements/<uuid:pk>/',        AnnouncementDetailView.as_view(),   name='announcement-detail'),
]