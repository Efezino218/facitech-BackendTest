from django.urls import path
from .views import (
    KYCStartView, KYCMyApplicationView,
    KYCStepPersonalView, KYCStepBusinessView, KYCStepShopsView,
    KYCStepIscooaStandingView, KYCStepStaffView, KYCStepNextOfKinView,
    KYCStepGuarantorView, KYCStepFinanceView, KYCStepEmergencyContactView,
    KYCStepDocumentsView, KYCStepDeclarationView,
    KYCQueueView, KYCDetailView,
    KYCApproveView, KYCRequestDocsView, KYCRejectView,
)
from .upload_views import (
    UploadPassportPhotoView, UploadIDFileView,
    UploadKYCDocumentsView, UploadShopPhotoView,
    KYCDocumentStatusView,
)

urlpatterns = [

    # ── Operator KYC step endpoints ─────────────────────────────────
    path('start/',                  KYCStartView.as_view(),                 name='kyc-start'),
    path('my-application/',         KYCMyApplicationView.as_view(),         name='kyc-my-application'),
    path('step/personal/',          KYCStepPersonalView.as_view(),          name='kyc-step-personal'),
    path('step/business/',          KYCStepBusinessView.as_view(),          name='kyc-step-business'),
    path('step/shops/',             KYCStepShopsView.as_view(),             name='kyc-step-shops'),
    path('step/iscooa-standing/',   KYCStepIscooaStandingView.as_view(),    name='kyc-step-iscooa-standing'),
    path('step/staff/',             KYCStepStaffView.as_view(),             name='kyc-step-staff'),
    path('step/next-of-kin/',       KYCStepNextOfKinView.as_view(),         name='kyc-step-next-of-kin'),
    path('step/guarantor/',         KYCStepGuarantorView.as_view(),         name='kyc-step-guarantor'),
    path('step/finance/',           KYCStepFinanceView.as_view(),           name='kyc-step-finance'),
    path('step/emergency-contact/', KYCStepEmergencyContactView.as_view(),  name='kyc-step-emergency'),
    path('step/documents/',         KYCStepDocumentsView.as_view(),         name='kyc-step-documents'),
    path('step/declaration/',       KYCStepDeclarationView.as_view(),       name='kyc-step-declaration'),

    # ── Operator file upload endpoints ──────────────────────────────
    path('upload/passport-photo/',          UploadPassportPhotoView.as_view(),  name='kyc-upload-passport'),
    path('upload/id-file/',                 UploadIDFileView.as_view(),         name='kyc-upload-id'),
    path('upload/documents/',               UploadKYCDocumentsView.as_view(),   name='kyc-upload-documents'),
    path('upload/shop-photo/<int:shop_id>/', UploadShopPhotoView.as_view(),     name='kyc-upload-shop-photo'),
    path('upload/status/',                  KYCDocumentStatusView.as_view(),    name='kyc-upload-status'),

    # ── ISCOOA Executive endpoints ──────────────────────────────────
    path('queue/',                  KYCQueueView.as_view(),                 name='kyc-queue'),
    path('<uuid:pk>/',              KYCDetailView.as_view(),                name='kyc-detail'),
    path('<uuid:pk>/approve/',      KYCApproveView.as_view(),               name='kyc-approve'),
    path('<uuid:pk>/request-docs/', KYCRequestDocsView.as_view(),           name='kyc-request-docs'),
    path('<uuid:pk>/reject/',       KYCRejectView.as_view(),                name='kyc-reject'),
]