from rest_framework import serializers
from .models import Bill, ExternalPayment
from validators import validate_billing_period


class BillSerializer(serializers.ModelSerializer):
    """
    Full bill serializer.
    Converts kobo amounts to Naira for display.
    """
    shop_number         = serializers.CharField(source='shop.shop_number', read_only=True)
    operator_name       = serializers.CharField(source='operator.full_name', read_only=True)
    verified_by_name    = serializers.CharField(source='verified_by.full_name', read_only=True)

    # Naira display fields (read only)
    management_fee_naira    = serializers.SerializerMethodField()
    maintenance_levy_naira  = serializers.SerializerMethodField()
    electricity_naira       = serializers.SerializerMethodField()
    water_naira             = serializers.SerializerMethodField()
    vat_naira               = serializers.SerializerMethodField()
    total_naira             = serializers.SerializerMethodField()

    # NEW: External payment info 
    has_external_payment   = serializers.SerializerMethodField()
    external_payment_count = serializers.SerializerMethodField()

    class Meta:
        model  = Bill
        fields = [
            'id', 'invoice_id', 'shop', 'shop_number',
            'operator', 'operator_name', 'billing_period',
            'management_fee', 'management_fee_naira',
            'maintenance_levy', 'maintenance_levy_naira',
            'electricity', 'electricity_naira',
            'water', 'water_naira',
            'vat', 'vat_naira',
            'total', 'total_naira',
            'status', 'paid_at', 'paid_ref',
            'verified_by', 'verified_by_name', 'verified_at',
            'has_external_payment',   # ← NEW
            'external_payment_count', # ← NEW
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'invoice_id', 'vat', 'total',
            'paid_at', 'paid_ref',
            'verified_by', 'verified_at',
            'created_at', 'updated_at',
        ]

    def get_management_fee_naira(self, obj):
        return obj.management_fee / 100

    def get_maintenance_levy_naira(self, obj):
        return obj.maintenance_levy / 100

    def get_electricity_naira(self, obj):
        return obj.electricity / 100

    def get_water_naira(self, obj):
        return obj.water / 100

    def get_vat_naira(self, obj):
        return obj.vat / 100

    def get_total_naira(self, obj):
        return obj.total / 100

    # NEW METHODS 
    def get_has_external_payment(self, obj):
        return obj.external_payments.exists()

    def get_external_payment_count(self, obj):
        return obj.external_payments.count()



class BillCreateSerializer(serializers.ModelSerializer):
    """
    Used by ISCOOA Treasurer to raise a new bill.
    Accepts amounts in kobo.
    """
    class Meta:
        model  = Bill
        fields = [
            'shop', 'billing_period',
            'management_fee', 'maintenance_levy',
            'electricity', 'water',
        ]

    def validate_billing_period(self, value):
        from django.core.exceptions import ValidationError as DjangoValidationError
        try:
            validate_billing_period(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(str(e.message) if hasattr(e, 'message') else str(e))
        return value

    def validate(self, data):
        # Prevent duplicate bill for same shop + period
        from .models import Bill
        if Bill.objects.filter(
            shop=data['shop'],
            billing_period=data['billing_period']
        ).exists():
            raise serializers.ValidationError(
                f"A bill already exists for shop "
                f"{data['shop'].shop_number} "
                f"in period {data['billing_period']}."
            )
        return data


class ExternalPaymentSerializer(serializers.ModelSerializer):
    operator_name    = serializers.CharField(source='operator.full_name', read_only=True)
    operator_email   = serializers.EmailField(source='operator.email', read_only=True)
    shop_number      = serializers.CharField(source='shop.shop_number', read_only=True)
    verified_by_name = serializers.CharField(source='verified_by.full_name', read_only=True)
    amount_naira     = serializers.ReadOnlyField()

    # Bill link details
    invoice_id       = serializers.CharField(source='bill.invoice_id', read_only=True)
    bill_status      = serializers.CharField(source='bill.status', read_only=True)
    bill_total_naira = serializers.SerializerMethodField()

    class Meta:
        model  = ExternalPayment
        fields = [
            'id', 'operator', 'operator_name', 'operator_email',
            'bill', 'invoice_id', 'bill_status', 'bill_total_naira',
            'shop', 'shop_number',
            'category', 'amount', 'amount_naira',
            'payment_date', 'billing_period',
            'channel', 'reference', 'note', 'evidence',
            'status', 'verified_by', 'verified_by_name',
            'verified_at', 'verified_amount',
            'rejection_note',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'operator', 'status',
            'verified_by', 'verified_at', 'verified_amount',
            'created_at', 'updated_at',
        ]

    def get_bill_total_naira(self, obj):
        if obj.bill:
            return obj.bill.total / 100
        return None


class ExternalPaymentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = ExternalPayment
        fields = [
            'bill',
            'shop', 'category', 'amount',
            'payment_date', 'billing_period',
            'channel', 'reference', 'note', 'evidence',
        ]

    def validate_billing_period(self, value):
        from django.core.exceptions import ValidationError as DjangoValidationError
        try:
            validate_billing_period(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(
                str(e.message) if hasattr(e, 'message') else str(e)
            )
        return value

    def validate_bill(self, bill):
        if bill is None:
            return bill
        request = self.context.get('request')
        if bill.operator != request.user:
            raise serializers.ValidationError(
                'This bill does not belong to you.'
            )
        if bill.status not in ['unpaid']:
            raise serializers.ValidationError(
                f'This bill is already {bill.status}. '
                f'Only unpaid bills can be linked to an external payment.'
            )
        # Check no pending external payment already exists for this bill
        from .models import ExternalPayment as EP
        existing = EP.objects.filter(
            bill   = bill,
            status = 'pending',
        ).exists()
        if existing:
            raise serializers.ValidationError(
                'This bill already has a pending external payment awaiting verification. '
                'Please wait for the Treasurer to verify or reject it before submitting another.'
            )
        return bill

    def validate_shop(self, shop):
        request = self.context.get('request')
        if shop.operator != request.user:
            raise serializers.ValidationError(
                'This shop does not belong to you.'
            )
        return shop

    def validate(self, data):
        bill = data.get('bill')

        if bill:
            # ── BILL IS LINKED — enforce exact amount ─────────────────
            # Amount must exactly match the bill total
            # No partial payments. No overpayments.
            submitted_amount = data.get('amount', 0)

            if submitted_amount != bill.total:
                raise serializers.ValidationError(
                    {
                        'amount': (
                            f'When paying a linked bill the amount must be exactly '
                            f'₦{bill.total/100:,.2f} (the full bill total). '
                            f'Partial payments and overpayments are not accepted. '
                            f'You submitted ₦{submitted_amount/100:,.2f}.'
                        )
                    }
                )

            # Auto-fill billing_period and shop from bill
            # These are locked to the bill values
            data['billing_period'] = bill.billing_period
            data['shop']           = bill.shop
            data['amount']         = bill.total  # Lock to exact bill amount

        else:
            # ── NO BILL LINKED — validate normally ────────────────────
            if not data.get('shop'):
                raise serializers.ValidationError(
                    {'shop': 'Shop is required when no bill is linked.'}
                )
            if not data.get('billing_period'):
                raise serializers.ValidationError(
                    {'billing_period': 'Billing period is required when no bill is linked.'}
                )
            if not data.get('amount') or data.get('amount', 0) <= 0:
                raise serializers.ValidationError(
                    {'amount': 'Amount must be greater than zero.'}
                )

        return data