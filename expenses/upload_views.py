import os
from django.core.exceptions import ValidationError
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser

from .models import Expense
from .permissions import IsIscooaExec
from validators import validate_document_file
from drf_spectacular.utils import extend_schema


def delete_old_file(file_field):
    if file_field and hasattr(file_field, 'path'):
        try:
            if os.path.isfile(file_field.path):
                os.remove(file_field.path)
        except Exception:
            pass


@extend_schema(tags=['Expenses'])
class UploadExpenseEvidenceView(APIView):
    """
    POST /api/v1/expenses/<id>/upload-evidence/
    ISCOOA Executive uploads evidence for an expense.
    Accepts: JPEG, PNG, PDF. Max: 5MB.
    Old file deleted when replaced.
    """
    permission_classes = [IsIscooaExec]
    parser_classes     = [MultiPartParser, FormParser]

    def post(self, request, pk):
        try:
            expense = Expense.objects.get(pk=pk)
        except Expense.DoesNotExist:
            return Response(
                {'detail': 'Expense not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if expense.raised_by != request.user:
            return Response(
                {'detail': 'Only the person who raised this expense can upload evidence.'},
                status=status.HTTP_403_FORBIDDEN
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

        # Delete old evidence before saving new one
        delete_old_file(expense.evidence)

        expense.evidence = file
        expense.save()

        return Response({
            'detail':       'Evidence uploaded successfully.',
            'expense_ref':  expense.expense_ref,
            'file_name':    file.name,
            'file_size':    f'{file.size / 1024:.1f}KB',
        })