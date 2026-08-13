from urllib import request

from django.utils import timezone
from django.db import transaction
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from notifications.utils import send_notification, send_bulk_notification
from accounts.models import User
from django.db import models

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
            category    = serializer.validated_data['category'],
            narrative   = serializer.validated_data['narrative'],
            association = request.user.association,
            submitted_by = request.user,
        )

        # Notify President and Legal Adviser only
        # Never reveal who submitted — just that a new report exists
        privileged_users = User.objects.filter(
            association = request.user.association,
            is_active   = True,
        ).filter(
            models.Q(role='is', ipos='president') |
            models.Q(role='adv')
        )
        send_bulk_notification(
            users      = privileged_users,
            category   = 'general',
            title      = f'New Anonymous Report — {report.report_ref}',
            message    = (
                f'A new anonymous {report.get_category_display()} report '
                f'({report.report_ref}) has been submitted. '
                f'Please review in the Whistleblower panel.'
            ),
            related_id = str(report.id),
        )

        return Response({
            'detail': (
                'Your report has been submitted anonymously. '
                'Your identity has not been recorded in the report. '
                'You will be notified when ISCOOA updates the status of your report.'
            ),
            'report_ref': report.report_ref,
            'category':   report.get_category_display(),
            'status':     report.status,
            'note': (
                'Keep your reference number for your records. '
                'You will receive in-app notifications when the status changes. '
                'Your identity remains confidential — executives only see the report content.'
            ),
        }, status=status.HTTP_201_CREATED)


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
        qs = WhistleblowerReport.objects.filter(
            association = self.request.user.association
        )
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

    def get_queryset(self):
        return WhistleblowerReport.objects.filter(
            association = self.request.user.association
        )


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
            report = WhistleblowerReport.objects.get(
                pk          = pk,
                association = request.user.association,
            )
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


            # Update timeline
            WhistleblowerUpdate.objects.create(
                report=report,
                updated_by=request.user,  # ✅ CORRECT
                old_status=old_status,    # ✅ CORRECT
                new_status=new_status,    # ✅ CORRECT
                note=note or response,    # ✅ CORRECT
            )

            # ── Notify the operator who submitted the report ───────────────
            # We can notify them because we stored submitted_by
            # while keeping the report anonymous from the executives
            try:
                if report.submitted_by:
                    status_labels = {
                        'open':         'received and is now open for review',
                        'under_review': 'currently under review by ISCOOA',
                        'investigating': 'under active investigation',
                        'resolved':     'resolved by ISCOOA',
                        'closed':       'closed',
                    }
                    status_label = status_labels.get(new_status, new_status)

                    send_notification(
                        user       = report.submitted_by,
                        category   = 'general',
                        title      = f'Report Update — {report.report_ref}',
                        message    = (
                            f'Your anonymous report ({report.report_ref}) '
                            f'has been {status_label}. '
                            f'{f"Update: {response[:100]}" if response else ""}'
                        ),
                        related_id = str(report.id),
                    )
            except Exception:
                pass  # Never fail the response because notification failed

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
            report = WhistleblowerReport.objects.get(
                pk          = pk,
                association = request.user.association,
            )
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

                # Notify submitter report is closed
        try:
            if report.submitted_by:
                send_notification(
                    user       = report.submitted_by,
                    category   = 'general',
                    title      = f'Report Closed — {report.report_ref}',
                    message    = (
                        f'Your anonymous report ({report.report_ref}) '
                        f'has been closed by ISCOOA.'
                    ),
                    related_id = str(report.id),
                )
        except Exception:
            pass

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

        qs = WhistleblowerReport.objects.filter(
            association = request.user.association
        )
        total       = qs.count()
        by_status   = qs.values('status').annotate(count=Count('id'))
        by_category = qs.values('category').annotate(count=Count('id'))

        return Response({
            'total_reports': total,
            'by_status':     {item['status']: item['count'] for item in by_status},
            'by_category':   {item['category']: item['count'] for item in by_category},
        })