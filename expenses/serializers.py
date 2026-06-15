from rest_framework import serializers
from .models import Expense, ExpenseApprovalStep, ExpenseStatus


class ExpenseApprovalStepSerializer(serializers.ModelSerializer):
    actor_name   = serializers.CharField(
        source='actor.full_name', read_only=True
    )
    role_display = serializers.CharField(
        source='get_role_display', read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display', read_only=True
    )

    class Meta:
        model  = ExpenseApprovalStep
        fields = [
            'id', 'step_number', 'role', 'role_display',
            'actor', 'actor_name',
            'status', 'status_display',
            'note', 'acted_at', 'created_at',
        ]
        read_only_fields = fields


class ExpenseSerializer(serializers.ModelSerializer):
    """Full expense serializer with approval trail."""
    raised_by_name      = serializers.CharField(
        source='raised_by.full_name', read_only=True
    )
    raised_by_role      = serializers.CharField(
        source='raised_by.ipos', read_only=True
    )
    amount_naira        = serializers.ReadOnlyField()
    category_display    = serializers.CharField(
        source='get_category_display', read_only=True
    )
    status_display      = serializers.CharField(
        source='get_status_display', read_only=True
    )
    approval_steps      = ExpenseApprovalStepSerializer(
        many=True, read_only=True
    )
    paid_by_name        = serializers.CharField(
        source='paid_by.full_name', read_only=True
    )

    class Meta:
        model  = Expense
        fields = [
            'id', 'expense_ref',
            'title', 'category', 'category_display',
            'amount', 'amount_naira',
            'description', 'evidence',
            'status', 'status_display',
            'raised_by', 'raised_by_name', 'raised_by_role',
            'raised_date', 'requires_bot',
            'paid_at', 'paid_by', 'paid_by_name', 'payment_ref',
            'approval_steps',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'expense_ref', 'status',
            'raised_by', 'raised_date', 'requires_bot',
            'paid_at', 'paid_by', 'payment_ref',
            'created_at', 'updated_at',
        ]


class ExpenseCreateSerializer(serializers.ModelSerializer):
    """Used by any ISCOOA Exec to raise a new expense."""
    class Meta:
        model  = Expense
        fields = [
            'title', 'category', 'amount',
            'description', 'evidence',
        ]


class ExpenseListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing expenses."""
    raised_by_name   = serializers.CharField(
        source='raised_by.full_name', read_only=True
    )
    amount_naira     = serializers.ReadOnlyField()
    category_display = serializers.CharField(
        source='get_category_display', read_only=True
    )
    status_display   = serializers.CharField(
        source='get_status_display', read_only=True
    )

    class Meta:
        model  = Expense
        fields = [
            'id', 'expense_ref', 'title',
            'category', 'category_display',
            'amount', 'amount_naira',
            'status', 'status_display',
            'raised_by_name', 'requires_bot',
            'raised_date', 'created_at',
        ]


class ExpenseActionSerializer(serializers.Serializer):
    """Used by approvers to approve or reject an expense step."""
    action = serializers.ChoiceField(choices=['approve', 'reject'])
    note   = serializers.CharField(required=False, allow_blank=True)


class MarkPaidSerializer(serializers.Serializer):
    """Used by Treasurer or President to mark expense as paid."""
    payment_ref = serializers.CharField()