from rest_framework import serializers
from .models import Wallet, WalletTransaction


class WalletTransactionSerializer(serializers.ModelSerializer):
    amount_naira = serializers.ReadOnlyField()

    class Meta:
        model  = WalletTransaction
        fields = [
            'id', 'type', 'amount', 'amount_naira',
            'description', 'method', 'reference',
            'confirmed', 'created_at',
        ]
        read_only_fields = fields


class WalletSerializer(serializers.ModelSerializer):
    """
    Full wallet serializer for operator view.
    Shows balance, Cool MFB account details,
    and recent transactions.
    """
    operator_email  = serializers.EmailField(source='operator.email', read_only=True)
    operator_name   = serializers.SerializerMethodField()
    balance_naira   = serializers.ReadOnlyField()
    transactions    = WalletTransactionSerializer(many=True, read_only=True)

    class Meta:
        model  = Wallet
        fields = [
            'id', 'operator_email', 'operator_name',
            'balance', 'balance_naira',
            'coolmfb_account_number', 'coolmfb_account_name',
            'is_active', 'created_at', 'updated_at',
            'transactions',
        ]
        read_only_fields = fields

    def get_operator_name(self, obj):
        """Return operator's full name or fallback to email"""
        return obj.operator.full_name or obj.operator.email


class TopUpSerializer(serializers.Serializer):
    """Used when operator tops up their wallet."""
    amount = serializers.IntegerField(
        min_value=10000,
        # minimum top-up is ₦100 (10000 kobo)
        help_text='Amount in kobo. e.g. 1000000 = ₦10,000'
    )
    method = serializers.ChoiceField(
        choices=WalletTransaction.Method.choices
    )

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                'Top-up amount must be greater than zero.'
            )
        return value