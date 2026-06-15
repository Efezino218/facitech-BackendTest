from django.urls import path
from .views import (
    SubmitReportView,
    AllReportsView, ReportDetailView,
    RespondToReportView, ArchiveReportView,
    ReportStatsView,
)

urlpatterns = [

    # ── Operator endpoints ──────────────────────────────────────────
    path('submit/',             SubmitReportView.as_view(),     name='wb-submit'),

    # ── President and Legal Adviser endpoints ───────────────────────
    path('all/',                AllReportsView.as_view(),       name='wb-all'),
    path('all/<uuid:pk>/',      ReportDetailView.as_view(),     name='wb-detail'),
    path('<uuid:pk>/respond/',  RespondToReportView.as_view(),  name='wb-respond'),
    path('<uuid:pk>/archive/',  ArchiveReportView.as_view(),    name='wb-archive'),
    path('stats/',              ReportStatsView.as_view(),      name='wb-stats'),
]