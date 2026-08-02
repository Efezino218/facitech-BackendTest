from django.urls import path
from .views import (
    SubmitAdvertView, MyAdvertsView, MyAdvertDetailView,
    MarketplaceView, DashboardCarouselView,
    AdvertQueueView, AdvertDetailAdminView,
    ApproveAdvertView, RejectAdvertView,
    TakeOfflineView, AdvertRevenueSummaryView,
)

urlpatterns = [

    # ── Operator endpoints ──────────────────────────────────────────
    path('submit/',                     SubmitAdvertView.as_view(),      name='submit-advert'),
    path('my-adverts/',                 MyAdvertsView.as_view(),         name='my-adverts'),
    path('my-adverts/<uuid:pk>/',       MyAdvertDetailView.as_view(),    name='my-advert-detail'),

    # ── Marketplace — all authenticated users ───────────────────────
    path('marketplace/',                MarketplaceView.as_view(),       name='advert-marketplace'),
    path('carousel/',                   DashboardCarouselView.as_view(), name='advert-carousel'),

    # ── Secretary General and President — view queue ────────────────
    path('queue/',                      AdvertQueueView.as_view(),       name='advert-queue'),
    path('queue/<uuid:pk>/',            AdvertDetailAdminView.as_view(), name='advert-queue-detail'),

    # ── Secretary General only — actions ───────────────────────────
    path('<uuid:pk>/approve/',          ApproveAdvertView.as_view(),     name='approve-advert'),
    path('<uuid:pk>/reject/',           RejectAdvertView.as_view(),      name='reject-advert'),
    path('<uuid:pk>/take-offline/',     TakeOfflineView.as_view(),       name='take-advert-offline'),

    # ── Revenue summary ─────────────────────────────────────────────
    path('revenue-summary/',            AdvertRevenueSummaryView.as_view(), name='advert-revenue-summary'),
]