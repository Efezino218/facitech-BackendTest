from django.utils import timezone
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response

from bills.models import Bill
from .models import ReconciliationRecord, PeriodSummary
from .serializers import (
    ReconciliationRecordSerializer,
    PeriodSummarySerializer,
    ManualReconcileSerializer,
)
from .permissions import IsTreasurer, IsIscooaExec
from .utils import reconcile_bill, reconcile_period
from drf_spectacular.utils import extend_schema

from validators import validate_billing_period
from django.core.exceptions import ValidationError as DjangoValidationError


@extend_schema(tags=['Reconciliation'])
class RunReconciliationView(APIView):
    """
    POST /api/v1/reconciliation/run/
    Treasurer runs reconciliation for a billing period.
    Creates or updates all reconciliation records for that period.
    Body: { "billing_period": "2026-05" }
    """
    permission_classes = [IsTreasurer]

    def post(self, request):
        billing_period = request.data.get('billing_period')
        if not billing_period:
            return Response(
                {'detail': 'billing_period is required. Format: YYYY-MM e.g. 2026-05'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            validate_billing_period(billing_period)
        except DjangoValidationError as e:
            return Response(
                {'detail': str(e.message) if hasattr(e, 'message') else str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check bills exist for this period
        bills = Bill.objects.filter(billing_period=billing_period)
        if not bills.exists():
            return Response(
                {'detail': f'No bills found for period {billing_period}.'},
                status=status.HTTP_404_NOT_FOUND
            )

        summary = reconcile_period(billing_period)

        return Response({
            'detail':               f'Reconciliation complete for {billing_period}.',
            'billing_period':       billing_period,
            'total_bills':          summary.total_bills,
            'matched_count':        summary.matched_count,
            'unverified_count':     summary.unverified_count,
            'gap_count':            summary.gap_count,
            'total_billed_naira':   summary.total_billed_naira,
            'total_paid_naira':     summary.total_paid_naira,
            'settlement_percentage': float(summary.settlement_percentage),
        })


@extend_schema(tags=['Reconciliation'])
class PeriodSummaryListView(generics.ListAPIView):
    """
    GET /api/v1/reconciliation/periods/
    Treasurer sees yearly summary —
    month by month breakdown of reconciliation.
    """
    serializer_class   = PeriodSummarySerializer
    permission_classes = [IsTreasurer]
    queryset           = PeriodSummary.objects.all()


@extend_schema(tags=['Reconciliation'])
class PeriodSummaryDetailView(generics.RetrieveAPIView):
    """
    GET /api/v1/reconciliation/periods/<billing_period>/
    Treasurer views detail for a specific period.
    e.g. /api/v1/reconciliation/periods/2026-05/
    """
    serializer_class   = PeriodSummarySerializer
    permission_classes = [IsTreasurer]

    def get_object(self):
        billing_period = self.kwargs.get('billing_period')
        try:
            return PeriodSummary.objects.get(
                billing_period=billing_period
            )
        except PeriodSummary.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound(
                f'No reconciliation summary found for period {billing_period}. '
                f'Run reconciliation first.'
            )


@extend_schema(tags=['Reconciliation'])
class ReconciliationLedgerView(generics.ListAPIView):
    """
    GET /api/v1/reconciliation/ledger/
    Dual-party ledger view.
    Per invoice — ISCOOA record vs Operator record.
    Filter by ?period=2026-05
    Filter by ?match_status=match|unverified|gap
    Filter by ?shop=B-11
    """
    serializer_class   = ReconciliationRecordSerializer
    permission_classes = [IsTreasurer]

    def get_queryset(self):
        qs = ReconciliationRecord.objects.all()

        period = self.request.query_params.get('period')
        if period:
            qs = qs.filter(billing_period=period)

        match_status = self.request.query_params.get('match_status')
        if match_status:
            qs = qs.filter(match_status=match_status)

        shop = self.request.query_params.get('shop')
        if shop:
            qs = qs.filter(shop__shop_number__icontains=shop)

        return qs


@extend_schema(tags=['Reconciliation'])
class ReconciliationRecordDetailView(generics.RetrieveAPIView):
    """
    GET /api/v1/reconciliation/ledger/<id>/
    Treasurer views full detail of a single
    reconciliation record.
    """
    serializer_class   = ReconciliationRecordSerializer
    permission_classes = [IsTreasurer]
    queryset           = ReconciliationRecord.objects.all()


@extend_schema(tags=['Reconciliation'])
class ManualReconcileView(APIView):
    """
    POST /api/v1/reconciliation/ledger/<id>/reconcile/
    Treasurer manually overrides the match status
    after reviewing a discrepancy.
    """
    permission_classes = [IsTreasurer]

    def post(self, request, pk):
        try:
            record = ReconciliationRecord.objects.get(pk=pk)
        except ReconciliationRecord.DoesNotExist:
            return Response(
                {'detail': 'Record not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = ManualReconcileSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        record.match_status    = serializer.validated_data['match_status']
        record.notes           = serializer.validated_data.get('notes', '')
        record.reconciled_by   = request.user
        record.reconciled_at   = timezone.now()
        record.save()

        return Response({
            'detail':        'Record manually reconciled.',
            'invoice_id':    record.bill.invoice_id,
            'match_status':  record.match_status,
            'notes':         record.notes,
            'reconciled_by': request.user.full_name,
        })


@extend_schema(tags=['Reconciliation'])
class ExportReconciliationView(APIView):
    """
    GET /api/v1/reconciliation/export/
    Treasurer exports reconciliation data as CSV.
    Filter by ?period=2026-05
    """
    permission_classes = [IsTreasurer]

    def get(self, request):
        import csv
        from django.http import HttpResponse

        period = request.query_params.get('period', '')
        qs     = ReconciliationRecord.objects.all()
        if period:
            qs = qs.filter(billing_period=period)

        filename = f'reconciliation_{period or "all"}.csv'
        response = HttpResponse(
            content_type='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"'
            },
        )

        writer = csv.writer(response)
        writer.writerow([
            'Invoice ID', 'Period', 'Shop', 'Operator',
            'ISCOOA Amount (₦)', 'Operator Amount (₦)',
            'Variance (₦)', 'Method', 'Paid Ref', 'Match Status',
            'Notes', 'Reconciled By', 'Reconciled At',
        ])

        for record in qs:
            writer.writerow([
                record.bill.invoice_id,
                record.billing_period,
                record.shop.shop_number,
                record.operator.full_name,
                record.iscooa_amount_naira,
                record.operator_amount_naira,
                record.variance_naira,
                record.operator_method,
                record.paid_ref,
                record.match_status,
                record.notes,
                record.reconciled_by.full_name if record.reconciled_by else '',
                record.reconciled_at.strftime('%Y-%m-%d %H:%M') if record.reconciled_at else '',
            ])

        return response


@extend_schema(tags=['Reconciliation'])
class OperatorReconciliationView(generics.ListAPIView):
    """
    GET /api/v1/reconciliation/my-records/
    Operator views their own reconciliation records.
    Shows them how ISCOOA sees their payment history.
    """
    serializer_class   = ReconciliationRecordSerializer
    permission_classes = [IsIscooaExec]

    def get_queryset(self):
        return ReconciliationRecord.objects.filter(
            operator=self.request.user
        )