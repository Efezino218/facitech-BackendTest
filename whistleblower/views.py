from django.utils import timezone
from django.db import transaction
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import WhistleblowerReport, WhistleblowerUpdate
from .serializers import (
    WhistleblowerReportSerializer,
    WhistleblowerSubmitSerializer,
    WhistleblowerListSerializer,
    WhistleblowerRespondSerializer,
)
from .permissions import IsOperator, IsPresidentOrLegalAdviser
from drf_spectacular.utils import extend_schema


# ─── OPERATOR VIEWS ───────────────────────────────────────────────────────────

@extend_schema(tags=['Whistleblower'])
class SubmitReportView(APIView):
    """
    POST /api/v1/whistleblower/submit/
    Operator submits an anonymous report.
    NO identity stored. Only category and narrative saved.
    """
    permission_classes = [IsOperator]

    def post(self, request):
        serializer = WhistleblowerSubmitSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        # Save with NO user reference whatsoever
        report = WhistleblowerReport.objects.create(
            category  = serializer.validated_data['category'],
            narrative = serializer.validated_data['narrative'],
        )

        return Response(
            {
                'detail':     'Your report has been submitted anonymously. Your identity has not been recorded.',
                'report_ref': report.report_ref,
                'category':   report.get_category_display(),
                'status':     report.status,
            },
            status=status.HTTP_201_CREATED
        )


# ─── PRESIDENT AND LEGAL ADVISER VIEWS ───────────────────────────────────────

@extend_schema(tags=['Whistleblower'])
class AllReportsView(generics.ListAPIView):
    """
    GET /api/v1/whistleblower/all/
    President and Legal Adviser see all reports.
    Filter by ?status=open|under_review|investigating|resolved|archived
    Filter by ?category=financial_irregularity|vendor_collusion etc
    """
    serializer_class   = WhistleblowerListSerializer
    permission_classes = [IsPresidentOrLegalAdviser]

    def get_queryset(self):
        qs = WhistleblowerReport.objects.all()
        report_status = self.request.query_params.get('status')
        if report_status:
            qs = qs.filter(status=report_status)
        category = self.request.query_params.get('category')
        if category:
            qs = qs.filter(category=category)
        return qs


@extend_schema(tags=['Whistleblower'])
class ReportDetailView(generics.RetrieveAPIView):
    """
    GET /api/v1/whistleblower/all/<id>/
    President and Legal Adviser view full report detail.
    """
    serializer_class   = WhistleblowerReportSerializer
    permission_classes = [IsPresidentOrLegalAdviser]
    queryset           = WhistleblowerReport.objects.all()


@extend_schema(tags=['Whistleblower'])
class RespondToReportView(APIView):
    """
    POST /api/v1/whistleblower/<id>/respond/
    President or Legal Adviser updates report status
    and adds investigation notes.
    """
    permission_classes = [IsPresidentOrLegalAdviser]

    def post(self, request, pk):
        try:
            report = WhistleblowerReport.objects.get(pk=pk)
        except WhistleblowerReport.DoesNotExist:
            return Response(
                {'detail': 'Report not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if report.status == WhistleblowerReport.Status.ARCHIVED:
            return Response(
                {'detail': 'Archived reports cannot be updated.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = WhistleblowerRespondSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        new_status  = serializer.validated_data['new_status']
        response    = serializer.validated_data['response']
        note        = serializer.validated_data.get('note', '')
        old_status  = report.status

        with transaction.atomic():
            report.status      = new_status
            report.response    = response
            report.assigned_to = request.user

            if new_status == WhistleblowerReport.Status.RESOLVED:
                report.resolved_at = timezone.now()

            report.save()

            WhistleblowerUpdate.objects.create(
                report     = report,
                updated_by = request.user,
                old_status = old_status,
                new_status = new_status,
                note       = note or response,
            )

        return Response({
            'detail':     'Report updated successfully.',
            'report_ref': report.report_ref,
            'old_status': old_status,
            'new_status': report.status,
        })


@extend_schema(tags=['Whistleblower'])
class ArchiveReportView(APIView):
    """
    POST /api/v1/whistleblower/<id>/archive/
    President archives a resolved or closed report.
    """
    permission_classes = [IsPresidentOrLegalAdviser]

    def post(self, request, pk):
        try:
            report = WhistleblowerReport.objects.get(pk=pk)
        except WhistleblowerReport.DoesNotExist:
            return Response(
                {'detail': 'Report not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if report.status == WhistleblowerReport.Status.ARCHIVED:
            return Response(
                {'detail': 'Report is already archived.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        old_status     = report.status
        report.status  = WhistleblowerReport.Status.ARCHIVED
        report.save()

        WhistleblowerUpdate.objects.create(
            report     = report,
            updated_by = request.user,
            old_status = old_status,
            new_status = WhistleblowerReport.Status.ARCHIVED,
            note       = 'Report archived.',
        )

        return Response({
            'detail':     'Report archived successfully.',
            'report_ref': report.report_ref,
        })


@extend_schema(tags=['Whistleblower'])
class ReportStatsView(APIView):
    """
    GET /api/v1/whistleblower/stats/
    President sees report statistics.
    """
    permission_classes = [IsPresidentOrLegalAdviser]

    def get(self, request):
        from django.db.models import Count

        total      = WhistleblowerReport.objects.count()
        by_status  = WhistleblowerReport.objects.values('status').annotate(count=Count('id'))
        by_category = WhistleblowerReport.objects.values('category').annotate(count=Count('id'))

        return Response({
            'total_reports': total,
            'by_status':     {item['status']: item['count'] for item in by_status},
            'by_category':   {item['category']: item['count'] for item in by_category},
        })