import os
from django.core.exceptions import ValidationError
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser

from .models import ExternalPayment
from .permissions import IsOperator
from validators import validate_document_file
from drf_spectacular.utils import extend_schema



def delete_old_file(file_field):
    if file_field and hasattr(file_field, 'path'):
        try:
            if os.path.isfile(file_field.path):
                os.remove(file_field.path)
        except Exception:
            pass


@extend_schema(tags=['Bills'])
class UploadExternalPaymentEvidenceView(APIView):
    """
    POST /api/v1/bills/external-payments/<id>/upload-evidence/
    Operator uploads evidence for an external payment.
    Accepts: JPEG, PNG, PDF. Max: 5MB.
    Old file deleted when replaced.
    """
    permission_classes = [IsOperator]
    parser_classes     = [MultiPartParser, FormParser]

    def post(self, request, pk):
        try:
            external_payment = ExternalPayment.objects.get(
                pk       = pk,
                operator = request.user
            )
        except ExternalPayment.DoesNotExist:
            return Response(
                {'detail': 'External payment not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if external_payment.status != 'pending':
            return Response(
                {'detail': 'Evidence can only be uploaded for pending payments.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        file = request.FILES.get('evidence')
        if not file:
            return Response(
                {'detail': 'No file provided. Please attach an evidence file.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            validate_document_file(file)
        except ValidationError as e:
            return Response(
                {'detail': str(e.message)},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Delete old evidence file before saving new one
        delete_old_file(external_payment.evidence)

        external_payment.evidence = file
        external_payment.save()

        return Response({
            'detail':    'Evidence uploaded successfully.',
            'file_name': file.name,
            'file_size': f'{file.size / 1024:.1f}KB',
            'status':    external_payment.status,
        })