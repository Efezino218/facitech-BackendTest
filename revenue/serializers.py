from rest_framework import serializers
from .models import RevenueWallet, RevenueTransaction, RevenueDistribution
from .models import WithdrawalRequest


class RevenueTransactionSerializer(serializers.ModelSerializer):
    amount_naira = serializers.ReadOnlyField()
    transaction_type_display = serializers.CharField(
        source='get_transaction_type_display', read_only=True
    )
    source_type_display = serializers.CharField(
        source='get_source_type_display', read_only=True
    )

    class Meta:
        model  = RevenueTransaction
        fields = [
            'id', 'transaction_type', 'transaction_type_display',
            'amount', 'amount_naira',
            'source_type', 'source_type_display',
            'source_ref', 'description', 'created_at',
        ]
        read_only_fields = fields


class RevenueWalletSerializer(serializers.ModelSerializer):
    balance_naira        = serializers.ReadOnlyField()
    total_earned_naira   = serializers.ReadOnlyField()
    total_withdrawn_naira = serializers.ReadOnlyField()
    association_name     = serializers.CharField(
        source='association.name', read_only=True
    )
    transactions         = RevenueTransactionSerializer(many=True, read_only=True)
    wallet_type_display  = serializers.CharField(
        source='get_wallet_type_display', read_only=True
    )

    class Meta:
        model  = RevenueWallet
        fields = [
            'id', 'name', 'wallet_type', 'wallet_type_display',
            'association', 'association_name',
            'balance', 'balance_naira',
            'total_earned', 'total_earned_naira',
            'total_withdrawn', 'total_withdrawn_naira',
            'created_at', 'updated_at',
            'transactions',
        ]
        read_only_fields = fields


class RevenueWalletSummarySerializer(serializers.ModelSerializer):
    """Lightweight wallet summary without transaction history."""
    balance_naira         = serializers.ReadOnlyField()
    total_earned_naira    = serializers.ReadOnlyField()
    total_withdrawn_naira = serializers.ReadOnlyField()
    association_name      = serializers.CharField(
        source='association.name', read_only=True
    )

    class Meta:
        model  = RevenueWallet
        fields = [
            'id', 'name', 'wallet_type',
            'association', 'association_name',
            'balance', 'balance_naira',
            'total_earned', 'total_earned_naira',
            'total_withdrawn', 'total_withdrawn_naira',
            'updated_at',
        ]
        read_only_fields = fields


class RevenueDistributionSerializer(serializers.ModelSerializer):
    association_name      = serializers.CharField(
        source='association.name', read_only=True
    )
    operator_email        = serializers.EmailField(
        source='operator.email', read_only=True
    )
    operator_name         = serializers.CharField(
        source='operator.full_name', read_only=True
    )
    total_amount_naira    = serializers.ReadOnlyField()
    association_amount_naira = serializers.ReadOnlyField()
    platform_amount_naira = serializers.ReadOnlyField()
    payment_type_display  = serializers.CharField(
        source='get_payment_type_display', read_only=True
    )

    class Meta:
        model  = RevenueDistribution
        fields = [
            'id', 'association', 'association_name',
            'operator', 'operator_email', 'operator_name',
            'payment_type', 'payment_type_display',
            'source_ref',
            'total_amount', 'total_amount_naira',
            'association_share_pct', 'platform_share_pct',
            'association_amount', 'association_amount_naira',
            'platform_amount', 'platform_amount_naira',
            'note', 'created_at',
        ]
        read_only_fields = fields





class WithdrawalRequestSerializer(serializers.ModelSerializer):
    """Full withdrawal request serializer."""
    amount_naira        = serializers.ReadOnlyField()
    revenue_wallet_name = serializers.CharField(
        source='revenue_wallet.name', read_only=True
    )
    requested_by_name   = serializers.CharField(
        source='requested_by.full_name', read_only=True
    )
    approved_by_name    = serializers.CharField(
        source='approved_by.full_name', read_only=True
    )
    rejected_by_name    = serializers.CharField(
        source='rejected_by.full_name', read_only=True
    )
    processed_by_name   = serializers.CharField(
        source='processed_by.full_name', read_only=True
    )
    status_display      = serializers.CharField(
        source='get_status_display', read_only=True
    )
    transfer_method_display = serializers.CharField(
        source='get_transfer_method_display', read_only=True
    )

    class Meta:
        model  = WithdrawalRequest
        fields = [
            'id', 'withdrawal_ref',
            'revenue_wallet', 'revenue_wallet_name',
            'requested_by', 'requested_by_name', 'requested_at',
            'amount', 'amount_naira',
            'reason', 'bank_name', 'account_number', 'account_name',
            'status', 'status_display',
            'approved_by', 'approved_by_name', 'approved_at', 'approval_note',
            'rejected_by', 'rejected_by_name', 'rejected_at', 'rejection_note',
            'processed_by', 'processed_by_name', 'processed_at',
            'transfer_method', 'transfer_method_display',
            'transfer_ref', 'processing_note',
            'updated_at',
        ]
        read_only_fields = [
            'id', 'withdrawal_ref', 'requested_by',
            'status', 'approved_by', 'approved_at',
            'rejected_by', 'rejected_at',
            'processed_by', 'processed_at',
            'updated_at',
        ]


class WithdrawalRequestCreateSerializer(serializers.ModelSerializer):
    """Used by Treasurer to create a withdrawal request."""
    class Meta:
        model  = WithdrawalRequest
        fields = [
            'amount', 'reason',
            'bank_name', 'account_number', 'account_name',
        ]

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                'Withdrawal amount must be greater than zero.'
            )
        # Minimum withdrawal ₦1,000
        if value < 100000:
            raise serializers.ValidationError(
                'Minimum withdrawal amount is ₦1,000 (100000 kobo).'
            )
        return value


class ProcessWithdrawalSerializer(serializers.Serializer):
    """Used by Super Admin to mark a withdrawal as processed."""
    transfer_method = serializers.ChoiceField(
        choices=WithdrawalRequest.TransferMethod.choices
    )
    transfer_ref    = serializers.CharField()
    processing_note = serializers.CharField(required=False, allow_blank=True)