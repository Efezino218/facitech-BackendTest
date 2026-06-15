from django.urls import path
from .views import (
    AuditLogListView, AuditLogDetailView,
    AuditStatsView, MyActivityView,
)

urlpatterns = [

    # ── Super Admin endpoints ───────────────────────────────────────
    path('',                AuditLogListView.as_view(),  name='audit-log'),
    path('stats/',          AuditStatsView.as_view(),    name='audit-stats'),
    path('<uuid:pk>/',      AuditLogDetailView.as_view(), name='audit-detail'),

    # ── President and Super Admin ───────────────────────────────────
    path('my-activity/',    MyActivityView.as_view(),    name='my-activity'),
]