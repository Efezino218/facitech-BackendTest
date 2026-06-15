from django.urls import path
from .views import (
    RaiseExpenseView, AllExpensesView, ExpenseDetailView,
    ApproveExpenseStepView, BOTRatifyExpenseView,
    MarkExpensePaidView, BOTPendingExpensesView,
    ExpenseStatsView,
)
from .upload_views import UploadExpenseEvidenceView

urlpatterns = [

    # ── ISCOOA Executive endpoints ──────────────────────────────────
    path('raise/',                      RaiseExpenseView.as_view(),         name='raise-expense'),
    path('',                            AllExpensesView.as_view(),          name='all-expenses'),
    path('stats/',                      ExpenseStatsView.as_view(),         name='expense-stats'),
    path('<uuid:pk>/',                  ExpenseDetailView.as_view(),        name='expense-detail'),
    path('<uuid:pk>/action/',           ApproveExpenseStepView.as_view(),   name='expense-action'),
    path('<uuid:pk>/mark-paid/',        MarkExpensePaidView.as_view(),      name='expense-mark-paid'),
    path('<uuid:pk>/upload-evidence/',  UploadExpenseEvidenceView.as_view(), name='upload-expense-evidence'),

    # ── BOT endpoints ───────────────────────────────────────────────
    path('bot-pending/',                BOTPendingExpensesView.as_view(),   name='bot-pending-expenses'),
    path('<uuid:pk>/bot-action/',       BOTRatifyExpenseView.as_view(),     name='bot-expense-action'),
]