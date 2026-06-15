from django.urls import path
from .views import (
    MyAdvertsView, SubmitAdvertView, MyAdvertDetailView,
    MarketplaceView,
    AdvertQueueView, AdvertDetailAdminView,
    ApproveAdvertView, RejectAdvertView,
    AdvertRevenueSummaryView,
)

urlpatterns = [

    # ── Operator endpoints ──────────────────────────────────────────
    path('my-adverts/',             MyAdvertsView.as_view(),         name='my-adverts'),
    path('submit/',                 SubmitAdvertView.as_view(),       name='submit-advert'),
    path('my-adverts/<uuid:pk>/',   MyAdvertDetailView.as_view(),     name='my-advert-detail'),
    path('marketplace/',            MarketplaceView.as_view(),        name='marketplace'),

    # ── Secretary General endpoints ─────────────────────────────────
    path('queue/',                  AdvertQueueView.as_view(),        name='advert-queue'),
    path('queue/<uuid:pk>/',        AdvertDetailAdminView.as_view(),  name='advert-admin-detail'),
    path('<uuid:pk>/approve/',      ApproveAdvertView.as_view(),      name='approve-advert'),
    path('<uuid:pk>/reject/',       RejectAdvertView.as_view(),       name='reject-advert'),
    path('revenue-summary/',        AdvertRevenueSummaryView.as_view(), name='advert-revenue-summary'),
]