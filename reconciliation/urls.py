from django.urls import path
from .views import (
    RunReconciliationView,
    PeriodSummaryListView, PeriodSummaryDetailView,
    ReconciliationLedgerView, ReconciliationRecordDetailView,
    ManualReconcileView, ExportReconciliationView,
    OperatorReconciliationView,
)

urlpatterns = [

    # ── Treasurer endpoints ─────────────────────────────────────────
    path('run/',                            RunReconciliationView.as_view(),        name='run-reconciliation'),
    path('periods/',                        PeriodSummaryListView.as_view(),        name='period-summaries'),
    path('periods/<str:billing_period>/',   PeriodSummaryDetailView.as_view(),      name='period-detail'),
    path('ledger/',                         ReconciliationLedgerView.as_view(),     name='reconciliation-ledger'),
    path('ledger/<uuid:pk>/',               ReconciliationRecordDetailView.as_view(), name='reconciliation-record-detail'),
    path('ledger/<uuid:pk>/reconcile/',     ManualReconcileView.as_view(),          name='manual-reconcile'),
    path('export/',                         ExportReconciliationView.as_view(),     name='reconciliation-export'),

    # ── Exec view ───────────────────────────────────────────────────
    path('my-records/',                     OperatorReconciliationView.as_view(),   name='my-reconciliation'),
]