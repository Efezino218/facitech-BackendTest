from rest_framework import serializers
from .models import ReconciliationRecord, PeriodSummary


class ReconciliationRecordSerializer(serializers.ModelSerializer):
    """Full reconciliation record serializer."""
    invoice_id          = serializers.CharField(
        source='bill.invoice_id', read_only=True
    )
    shop_number         = serializers.CharField(
        source='shop.shop_number', read_only=True
    )
    operator_name       = serializers.CharField(
        source='operator.full_name', read_only=True
    )
    operator_email      = serializers.EmailField(
        source='operator.email', read_only=True
    )
    reconciled_by_name  = serializers.CharField(
        source='reconciled_by.full_name', read_only=True
    )
    iscooa_amount_naira   = serializers.ReadOnlyField()
    operator_amount_naira = serializers.ReadOnlyField()
    variance_naira        = serializers.ReadOnlyField()
    match_status_display  = serializers.CharField(
        source='get_match_status_display', read_only=True
    )
    bill_status           = serializers.CharField(
        source='bill.status', read_only=True
    )

    class Meta:
        model  = ReconciliationRecord
        fields = [
            'id', 'invoice_id', 'billing_period',
            'operator', 'operator_name', 'operator_email',
            'shop', 'shop_number',
            'iscooa_amount', 'iscooa_amount_naira',
            'operator_amount', 'operator_amount_naira',
            'variance', 'variance_naira',
            'operator_method', 'paid_ref',
            'match_status', 'match_status_display',
            'bill_status', 'notes',
            'reconciled_by', 'reconciled_by_name',
            'reconciled_at', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'invoice_id', 'billing_period',
            'operator', 'shop',
            'iscooa_amount', 'operator_amount', 'variance',
            'match_status', 'reconciled_by', 'reconciled_at',
            'created_at', 'updated_at',
        ]


class PeriodSummarySerializer(serializers.ModelSerializer):
    """Period summary serializer."""
    total_billed_naira    = serializers.ReadOnlyField()
    total_paid_naira      = serializers.ReadOnlyField()
    total_variance_naira  = serializers.ReadOnlyField()

    class Meta:
        model  = PeriodSummary
        fields = [
            'id', 'billing_period',
            'total_bills',
            'matched_count', 'unverified_count', 'gap_count',
            'total_billed', 'total_billed_naira',
            'total_paid', 'total_paid_naira',
            'total_variance', 'total_variance_naira',
            'external_payments_count',
            'external_payments_amount',
            'settlement_percentage',
            'last_updated',
        ]
        read_only_fields = fields


class ManualReconcileSerializer(serializers.Serializer):
    """
    Used by Treasurer to manually mark a record
    after reviewing discrepancies.
    """
    match_status = serializers.ChoiceField(
        choices=ReconciliationRecord.MatchStatus.choices
    )
    notes        = serializers.CharField(required=False, allow_blank=True)