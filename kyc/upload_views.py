import os
from django.core.exceptions import ValidationError
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser

from .models import KYCApplication, KYCPersonal, KYCDocuments, KYCShop
from .permissions import IsOperator
from validators import validate_image_file, validate_document_file
from drf_spectacular.utils import extend_schema


# ─── ALLOWED KYC UPLOAD STATUSES ─────────────────────────────────────────────
UPLOAD_ALLOWED_STATUSES = ['submitted', 'docs_requested', 'rejected']
# not_started means no application yet so we handle that separately


def delete_old_file(file_field):
    """
    Deletes the old file from disk when a new one is uploaded.
    Safely handles cases where the file does not exist.
    """
    if file_field and hasattr(file_field, 'path'):
        try:
            if os.path.isfile(file_field.path):
                os.remove(file_field.path)
        except Exception:
            # Never crash the upload because of a cleanup failure
            pass


def check_upload_allowed(application):
    """
    Returns None if upload is allowed.
    Returns a Response object if upload should be blocked.
    """
    if application.status == 'approved':
        return Response(
            {
                'detail': (
                    'Uploads are not allowed after KYC has been approved. '
                    'Your KYC verification is complete. '
                    'If you need to update your documents please contact ISCOOA.'
                )
            },
            status=status.HTTP_403_FORBIDDEN
        )
    return None


@extend_schema(tags=['KYC'])
class UploadPassportPhotoView(APIView):
    """
    POST /api/v1/kyc/upload/passport-photo/
    Operator uploads their passport photo.
    Accepts: JPEG, PNG. Max: 5MB.
    Blocked after KYC approval.
    Old file deleted when replaced.
    """
    permission_classes = [IsOperator]
    parser_classes     = [MultiPartParser, FormParser]

    def post(self, request):
        try:
            application = request.user.kyc_application
        except KYCApplication.DoesNotExist:
            return Response(
                {'detail': 'No KYC application found. Please start one first.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Block uploads after approval
        blocked = check_upload_allowed(application)
        if blocked:
            return blocked

        file = request.FILES.get('passport_photo')
        if not file:
            return Response(
                {'detail': 'No file provided. Please attach a passport_photo file.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            validate_image_file(file)
        except ValidationError as e:
            return Response(
                {'detail': str(e.message)},
                status=status.HTTP_400_BAD_REQUEST
            )

        personal, _ = KYCPersonal.objects.get_or_create(application=application)

        # Delete old file before saving new one
        delete_old_file(personal.passport_photo)

        personal.passport_photo = file
        personal.save()

        return Response({
            'detail':    'Passport photo uploaded successfully.',
            'file_name': file.name,
            'file_size': f'{file.size / 1024:.1f}KB',
            'saved_to':  str(personal.passport_photo),
            'kyc_status': application.status,
        })


@extend_schema(tags=['KYC'])
class UploadIDFileView(APIView):
    """
    POST /api/v1/kyc/upload/id-file/
    Operator uploads their government ID.
    Accepts: JPEG, PNG, PDF. Max: 5MB.
    Blocked after KYC approval.
    Old file deleted when replaced.
    """
    permission_classes = [IsOperator]
    parser_classes     = [MultiPartParser, FormParser]

    def post(self, request):
        try:
            application = request.user.kyc_application
        except KYCApplication.DoesNotExist:
            return Response(
                {'detail': 'No KYC application found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        blocked = check_upload_allowed(application)
        if blocked:
            return blocked

        file = request.FILES.get('id_file')
        if not file:
            return Response(
                {'detail': 'No file provided. Please attach an id_file.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            validate_document_file(file)
        except ValidationError as e:
            return Response(
                {'detail': str(e.message)},
                status=status.HTTP_400_BAD_REQUEST
            )

        personal, _ = KYCPersonal.objects.get_or_create(application=application)

        # Delete old file before saving new one
        delete_old_file(personal.id_file)

        personal.id_file = file
        personal.save()

        return Response({
            'detail':     'Government ID uploaded successfully.',
            'file_name':  file.name,
            'file_size':  f'{file.size / 1024:.1f}KB',
            'saved_to':   str(personal.id_file),
            'kyc_status': application.status,
        })


@extend_schema(tags=['KYC'])
class UploadKYCDocumentsView(APIView):
    """
    POST /api/v1/kyc/upload/documents/
    Operator uploads all KYC documents in one request.
    Each field is optional — upload one or more at a time.
    Blocked after KYC approval.
    Old files deleted when replaced.

    Fields accepted:
        passport_photo  — JPEG/PNG image
        gov_id          — JPEG/PNG/PDF
        cac_certificate — JPEG/PNG/PDF
        tenancy_lease   — JPEG/PNG/PDF
        shop_photo      — JPEG/PNG image
    """
    permission_classes = [IsOperator]
    parser_classes     = [MultiPartParser, FormParser]

    def post(self, request):
        try:
            application = request.user.kyc_application
        except KYCApplication.DoesNotExist:
            return Response(
                {'detail': 'No KYC application found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        blocked = check_upload_allowed(application)
        if blocked:
            return blocked

        documents, _ = KYCDocuments.objects.get_or_create(application=application)
        uploaded = {}
        errors   = {}

        # Passport photo — image only
        if 'passport_photo' in request.FILES:
            file = request.FILES['passport_photo']
            try:
                validate_image_file(file)
                delete_old_file(documents.passport_photo)
                documents.passport_photo = file
                uploaded['passport_photo'] = file.name
            except ValidationError as e:
                errors['passport_photo'] = str(e.message)

        # Government ID — image or PDF
        if 'gov_id' in request.FILES:
            file = request.FILES['gov_id']
            try:
                validate_document_file(file)
                delete_old_file(documents.gov_id)
                documents.gov_id = file
                uploaded['gov_id'] = file.name
            except ValidationError as e:
                errors['gov_id'] = str(e.message)

        # CAC certificate — image or PDF
        if 'cac_certificate' in request.FILES:
            file = request.FILES['cac_certificate']
            try:
                validate_document_file(file)
                delete_old_file(documents.cac_certificate)
                documents.cac_certificate = file
                uploaded['cac_certificate'] = file.name
            except ValidationError as e:
                errors['cac_certificate'] = str(e.message)

        # Tenancy or lease agreement — image or PDF
        if 'tenancy_lease' in request.FILES:
            file = request.FILES['tenancy_lease']
            try:
                validate_document_file(file)
                delete_old_file(documents.tenancy_lease)
                documents.tenancy_lease = file
                uploaded['tenancy_lease'] = file.name
            except ValidationError as e:
                errors['tenancy_lease'] = str(e.message)

        # Shop front photo — image only
        if 'shop_photo' in request.FILES:
            file = request.FILES['shop_photo']
            try:
                validate_image_file(file)
                delete_old_file(documents.shop_photo)
                documents.shop_photo = file
                uploaded['shop_photo'] = file.name
            except ValidationError as e:
                errors['shop_photo'] = str(e.message)

        if not uploaded and not errors:
            return Response(
                {'detail': 'No files provided. Please attach at least one document.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if uploaded:
            documents.save()

        return Response({
            'detail':     f'{len(uploaded)} file(s) uploaded successfully.',
            'uploaded':   uploaded,
            'errors':     errors,
            'kyc_status': application.status,
        })


@extend_schema(tags=['KYC'])
class UploadShopPhotoView(APIView):
    """
    POST /api/v1/kyc/upload/shop-photo/<shop_id>/
    Operator uploads a photo for a specific KYC shop record.
    Accepts: JPEG, PNG. Max: 5MB.
    Blocked after KYC approval.
    Old file deleted when replaced.
    """
    permission_classes = [IsOperator]
    parser_classes     = [MultiPartParser, FormParser]

    def post(self, request, shop_id):
        try:
            application = request.user.kyc_application
            kyc_shop    = KYCShop.objects.get(
                id          = shop_id,
                application = application
            )
        except KYCApplication.DoesNotExist:
            return Response(
                {'detail': 'No KYC application found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except KYCShop.DoesNotExist:
            return Response(
                {'detail': 'KYC shop record not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        blocked = check_upload_allowed(application)
        if blocked:
            return blocked

        file = request.FILES.get('shop_photo')
        if not file:
            return Response(
                {'detail': 'No file provided. Please attach a shop_photo.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            validate_image_file(file)
        except ValidationError as e:
            return Response(
                {'detail': str(e.message)},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Delete old file before saving new one
        delete_old_file(kyc_shop.shop_photo)

        kyc_shop.shop_photo = file
        kyc_shop.save()

        return Response({
            'detail':      'Shop photo uploaded successfully.',
            'shop_number': kyc_shop.shop_number,
            'file_name':   file.name,
            'file_size':   f'{file.size / 1024:.1f}KB',
            'kyc_status':  application.status,
        })


@extend_schema(tags=['KYC'])
class KYCDocumentStatusView(APIView):
    """
    GET /api/v1/kyc/upload/status/
    Operator checks which documents have been uploaded.
    Shows a checklist of uploaded vs missing documents.
    Also shows whether uploads are currently allowed.
    """
    permission_classes = [IsOperator]

    def get(self, request):
        try:
            application = request.user.kyc_application
        except KYCApplication.DoesNotExist:
            return Response(
                {'detail': 'No KYC application found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Personal documents
        personal         = getattr(application, 'personal', None)
        passport_uploaded = bool(personal and personal.passport_photo)
        id_uploaded       = bool(personal and personal.id_file)

        # KYC documents
        docs      = getattr(application, 'documents', None)
        checklist = {
            'passport_photo':  bool(docs and docs.passport_photo),
            'gov_id':          bool(docs and docs.gov_id),
            'cac_certificate': bool(docs and docs.cac_certificate),
            'tenancy_lease':   bool(docs and docs.tenancy_lease),
            'shop_photo':      bool(docs and docs.shop_photo),
        }

        # KYC shop photos
        kyc_shops   = application.kyc_shops.all()
        shop_photos = {}
        for shop in kyc_shops:
            shop_photos[shop.shop_number] = bool(shop.shop_photo)

        total_required = 5
        total_uploaded = sum(1 for v in checklist.values() if v)

        # Whether uploads are currently allowed
        uploads_allowed  = application.status != 'approved'
        uploads_blocked_reason = None
        if not uploads_allowed:
            uploads_blocked_reason = (
                'Your KYC has been approved. '
                'Document uploads are locked. '
                'Contact ISCOOA if you need to update your documents.'
            )

        return Response({
            'kyc_id':     application.kyc_id,
            'kyc_status': application.status,
            'uploads_allowed':        uploads_allowed,
            'uploads_blocked_reason': uploads_blocked_reason,
            'personal_documents': {
                'passport_photo': passport_uploaded,
                'id_file':        id_uploaded,
            },
            'kyc_documents':  checklist,
            'shop_photos':    shop_photos,
            'progress': {
                'uploaded':   total_uploaded,
                'required':   total_required,
                'complete':   total_uploaded == total_required,
                'percentage': f'{(total_uploaded / total_required * 100):.0f}%',
            },
        })