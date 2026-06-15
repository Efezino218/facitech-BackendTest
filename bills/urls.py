from django.urls import path
from .views import (
    MyBillsView, MyBillDetailView, PayBillView,
    MyExternalPaymentsView, RegisterExternalPaymentView,
    AllBillsView, RaiseBillView, VerifyBillView,
    AllExternalPaymentsView,
    VerifyExternalPaymentView, RejectExternalPaymentView,
)
from .upload_views import UploadExternalPaymentEvidenceView

urlpatterns = [

    # ── Operator bill endpoints ─────────────────────────────────────
    path('my-bills/',                               MyBillsView.as_view(),                  name='my-bills'),
    path('my-bills/<uuid:pk>/',                     MyBillDetailView.as_view(),             name='my-bill-detail'),
    path('my-bills/<uuid:pk>/pay/',                 PayBillView.as_view(),                  name='pay-bill'),

    # ── Operator external payment endpoints ─────────────────────────
    path('external-payments/',                      MyExternalPaymentsView.as_view(),       name='my-external-payments'),
    path('external-payments/register/',             RegisterExternalPaymentView.as_view(),  name='register-external-payment'),
    path('external-payments/<uuid:pk>/upload-evidence/', UploadExternalPaymentEvidenceView.as_view(), name='upload-evidence'),

    # ── ISCOOA Executive bill endpoints ─────────────────────────────
    path('all/',                                    AllBillsView.as_view(),                 name='all-bills'),
    path('raise/',                                  RaiseBillView.as_view(),                name='raise-bill'),
    path('<uuid:pk>/verify/',                       VerifyBillView.as_view(),               name='verify-bill'),

    # ── ISCOOA Executive external payment endpoints ─────────────────
    path('external-payments/all/',                  AllExternalPaymentsView.as_view(),      name='all-external-payments'),
    path('external-payments/<uuid:pk>/verify/',     VerifyExternalPaymentView.as_view(),    name='verify-external-payment'),
    path('external-payments/<uuid:pk>/reject/',     RejectExternalPaymentView.as_view(),    name='reject-external-payment'),
]