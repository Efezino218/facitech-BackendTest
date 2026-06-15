from django.urls import path
from .views import (
    AssociationListView, AssociationCreateView,
    AssociationDetailView, UpdateAssociationConfigView,
    PublicConfigView, AssociationStatsView,
    PublicAssociationListView,
)

urlpatterns = [
    path('',                            AssociationListView.as_view(),      name='association-list'),
    path('public/',                     PublicAssociationListView.as_view(), name='public-association-list'),
    path('create/',                     AssociationCreateView.as_view(),    name='association-create'),
    path('config/<str:slug>/',          PublicConfigView.as_view(),         name='public-config'),
    path('<uuid:pk>/',                  AssociationDetailView.as_view(),    name='association-detail'),
    path('<uuid:pk>/config/',           UpdateAssociationConfigView.as_view(), name='update-config'),
    path('<uuid:pk>/stats/',            AssociationStatsView.as_view(),     name='association-stats'),
]