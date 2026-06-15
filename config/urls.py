from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

urlpatterns = [
    # ── Django Admin ────────────────────────────────────────────────
    path('admin/', admin.site.urls),

    # ── API Documentation ───────────────────────────────────────────
    path('api/schema/',     SpectacularAPIView.as_view(),       name='schema'),
    path('api/docs/',       SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/',      SpectacularRedocView.as_view(url_name='schema'),   name='redoc'),

    # ── Auth & Accounts ─────────────────────────────────────────────
    path('api/v1/auth/',          include('accounts.urls')),
    path('api/v1/overview/',      include('accounts.overview_urls')),

    # ── Core Modules ────────────────────────────────────────────────
    path('api/v1/kyc/',           include('kyc.urls')),
    path('api/v1/shops/',         include('shops.urls')),
    path('api/v1/bills/',         include('bills.urls')),
    path('api/v1/subscriptions/', include('subscriptions.urls')),
    path('api/v1/wallet/',        include('wallet.urls')),
    path('api/v1/adverts/',       include('adverts.urls')),
    path('api/v1/toilet/',        include('toilet.urls')),
    path('api/v1/disputes/',      include('disputes.urls')),
    path('api/v1/polls/',         include('polls.urls')),
    path('api/v1/whistleblower/', include('whistleblower.urls')),
    path('api/v1/notifications/', include('notifications.urls')),
    path('api/v1/enforcement/',   include('enforcement.urls')),
    path('api/v1/audit/',         include('audit.urls')),
    path('api/v1/publications/',  include('publications.urls')),
    path('api/v1/resolutions/',   include('resolutions.urls')),
    path('api/v1/expenses/',      include('expenses.urls')),
    path('api/v1/reconciliation/', include('reconciliation.urls')),
    path('api/v1/associations/', include('associations.urls')),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)