from django.urls import path
from .views import (
    MyShopsView, ShopCreateView, ShopDetailView,
    MyStaffView, StaffCreateView, StaffDetailView,
    AllShopsView, ShopAdminDetailView,
)

urlpatterns = [

    # ── Operator shop endpoints ─────────────────────────────────────
    path('my-shops/',           MyShopsView.as_view(),        name='my-shops'),
    path('create/',             ShopCreateView.as_view(),      name='shop-create'),
    path('<uuid:pk>/',          ShopDetailView.as_view(),      name='shop-detail'),

    # ── Operator staff endpoints ────────────────────────────────────
    path('my-staff/',           MyStaffView.as_view(),         name='my-staff'),
    path('my-staff/add/',       StaffCreateView.as_view(),     name='staff-add'),
    path('my-staff/<uuid:pk>/', StaffDetailView.as_view(),     name='staff-detail'),

    # ── ISCOOA Executive endpoints ──────────────────────────────────
    path('all/',                AllShopsView.as_view(),        name='all-shops'),
    path('all/<uuid:pk>/',      ShopAdminDetailView.as_view(), name='shop-admin-detail'),
]