from django.core.exceptions import ValidationError
from django.conf import settings
import re
from django.core.exceptions import ValidationError



def validate_file_size(file):
    """
    Validates that uploaded file does not exceed 5MB.
    Used across KYC, bills evidence and expense evidence.
    """
    max_size = 5 * 1024 * 1024  # 5MB in bytes
    if file.size > max_size:
        raise ValidationError(
            f'File size {file.size / (1024*1024):.1f}MB exceeds '
            f'the maximum allowed size of 5MB.'
        )


def validate_image_file(file):
    """
    Validates that uploaded file is a JPEG or PNG image.
    Used for passport photos and shop front photos.
    """
    validate_file_size(file)
    allowed_types = ['image/jpeg', 'image/png', 'image/jpg']
    if hasattr(file, 'content_type'):
        if file.content_type not in allowed_types:
            raise ValidationError(
                f'File type "{file.content_type}" is not allowed. '
                f'Please upload a JPEG or PNG image.'
            )


def validate_document_file(file):
    """
    Validates that uploaded file is a JPEG, PNG or PDF.
    Used for government IDs, CAC certificates and tenancy docs.
    """
    validate_file_size(file)
    allowed_types = ['image/jpeg', 'image/png', 'image/jpg', 'application/pdf']
    if hasattr(file, 'content_type'):
        if file.content_type not in allowed_types:
            raise ValidationError(
                f'File type "{file.content_type}" is not allowed. '
                f'Please upload a JPEG, PNG or PDF file.'
            )



def validate_billing_period(value):
    """
    Validates billing_period format: YYYY-MM
    Month must be 01-12.
    Used across bills, external payments and reconciliation.
    """
    if not re.match(r'^\d{4}-\d{2}$', str(value)):
        raise ValidationError(
            f'"{value}" is not a valid billing period. '
            f'Format must be YYYY-MM, e.g. 2026-05.'
        )

    year_str, month_str = str(value).split('-')
    month = int(month_str)

    if month < 1 or month > 12:
        raise ValidationError(
            f'"{value}" is not a valid billing period. '
            f'Month must be between 01 and 12, got "{month_str}".'
        )

    year = int(year_str)
    if year < 2020 or year > 2100:
        raise ValidationError(
            f'"{value}" is not a valid billing period. '
            f'Year "{year_str}" looks incorrect.'
        )