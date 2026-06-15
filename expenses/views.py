from django.utils import timezone
from django.db import transaction
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import (
    Expense, ExpenseApprovalStep,
    ExpenseStatus, create_approval_steps
)
from .serializers import (
    ExpenseSerializer, ExpenseCreateSerializer,
    ExpenseListSerializer, ExpenseActionSerializer,
    MarkPaidSerializer,
)
from .permissions import (
    IsIscooaExec, IsTreasurer, IsSecretaryGeneral,
    IsPresident, IsBOTMember, IsTreasurerOrPresident,
)
from drf_spectacular.utils import extend_schema


@extend_schema(tags=['Expenses'])
class RaiseExpenseView(generics.CreateAPIView):
    """
    POST /api/v1/expenses/raise/
    Any ISCOOA Executive raises a new expense.
    Approval steps are created automatically.
    """
    serializer_class   = ExpenseCreateSerializer
    permission_classes = [IsIscooaExec]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            expense = serializer.save(raised_by=request.user)
            create_approval_steps(expense)

        return Response(
            {
                'detail':       'Expense raised successfully.',
                'expense_ref':  expense.expense_ref,
                'amount_naira': expense.amount_naira,
                'status':       expense.status,
                'requires_bot': expense.requires_bot,
                'next_step':    'Awaiting Treasurer approval.',
            },
            status=status.HTTP_201_CREATED
        )


@extend_schema(tags=['Expenses'])
class AllExpensesView(generics.ListAPIView):
    """
    GET /api/v1/expenses/
    All ISCOOA Executives see all expenses.
    Filter by ?status=pending_treasurer|pending_secretary etc
    Filter by ?category=facility_maintenance etc
    """
    serializer_class   = ExpenseListSerializer
    permission_classes = [IsIscooaExec]

    def get_queryset(self):
        qs = Expense.objects.all()
        exp_status = self.request.query_params.get('status')
        if exp_status:
            qs = qs.filter(status=exp_status)
        category = self.request.query_params.get('category')
        if category:
            qs = qs.filter(category=category)
        return qs


@extend_schema(tags=['Expenses'])
class ExpenseDetailView(generics.RetrieveAPIView):
    """
    GET /api/v1/expenses/<id>/
    View full expense with complete approval trail.
    """
    serializer_class   = ExpenseSerializer
    permission_classes = [IsIscooaExec]
    queryset           = Expense.objects.all()


@extend_schema(tags=['Expenses'])
class ApproveExpenseStepView(APIView):
    """
    POST /api/v1/expenses/<id>/action/
    The current step approver approves or rejects.
    Automatically advances to next step on approval.
    Terminates the expense on rejection.
    """
    permission_classes = [IsIscooaExec]

    def post(self, request, pk):
        try:
            expense = Expense.objects.get(pk=pk)
        except Expense.DoesNotExist:
            return Response(
                {'detail': 'Expense not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if expense.status in [
            ExpenseStatus.APPROVED,
            ExpenseStatus.PAID,
            ExpenseStatus.REJECTED
        ]:
            return Response(
                {'detail': f'This expense is already {expense.status}.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = ExpenseActionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        action = serializer.validated_data['action']
        note   = serializer.validated_data.get('note', '')

        # Determine which step this user can action
        user_role = request.user.ipos
        role_to_status_map = {
            'treasurer':         ExpenseStatus.PENDING_TREASURER,
            'secretary_general': ExpenseStatus.PENDING_SECRETARY,
            'president':         ExpenseStatus.PENDING_PRESIDENT,
        }

        expected_status = role_to_status_map.get(user_role)
        if not expected_status or expense.status != expected_status:
            return Response(
                {
                    'detail': f'This expense is not awaiting your approval. Current status: {expense.status}.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Find the current pending step
        step_number_map = {
            'treasurer':         1,
            'secretary_general': 2,
            'president':         3,
        }
        step_number = step_number_map.get(user_role)

        try:
            step = ExpenseApprovalStep.objects.get(
                expense     = expense,
                step_number = step_number,
                status      = ExpenseApprovalStep.StepStatus.PENDING,
            )
        except ExpenseApprovalStep.DoesNotExist:
            return Response(
                {'detail': 'Approval step not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        with transaction.atomic():
            # Record this step
            step.actor    = request.user
            step.note     = note
            step.acted_at = timezone.now()

            if action == 'approve':
                step.status = ExpenseApprovalStep.StepStatus.APPROVED
                step.save()

                # Advance to next step
                if user_role == 'treasurer':
                    expense.status = ExpenseStatus.PENDING_SECRETARY
                    next_step_msg  = 'Awaiting Secretary General approval.'
                elif user_role == 'secretary_general':
                    expense.status = ExpenseStatus.PENDING_PRESIDENT
                    next_step_msg  = 'Awaiting President approval.'
                elif user_role == 'president':
                    if expense.requires_bot:
                        expense.status = ExpenseStatus.PENDING_BOT
                        next_step_msg  = 'Awaiting BOT ratification.'
                    else:
                        expense.status = ExpenseStatus.APPROVED
                        next_step_msg  = 'Expense fully approved.'
                expense.save()

            else:
                # Rejected
                step.status = ExpenseApprovalStep.StepStatus.REJECTED
                step.save()
                expense.status = ExpenseStatus.REJECTED
                expense.save()
                next_step_msg = 'Expense rejected.'

        return Response({
            'detail':       f'Expense {action}d successfully.',
            'expense_ref':  expense.expense_ref,
            'status':       expense.status,
            'next_step':    next_step_msg,
        })


@extend_schema(tags=['Expenses'])
class BOTRatifyExpenseView(APIView):
    """
    POST /api/v1/expenses/<id>/bot-action/
    BOT member ratifies or rejects a high-value expense.
    Only for expenses with status pending_bot.
    """
    permission_classes = [IsBOTMember]

    def post(self, request, pk):
        try:
            expense = Expense.objects.get(pk=pk)
        except Expense.DoesNotExist:
            return Response(
                {'detail': 'Expense not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if expense.status != ExpenseStatus.PENDING_BOT:
            return Response(
                {'detail': 'This expense is not awaiting BOT ratification.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = ExpenseActionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        action = serializer.validated_data['action']
        note   = serializer.validated_data.get('note', '')

        try:
            step = ExpenseApprovalStep.objects.get(
                expense     = expense,
                step_number = 4,
                status      = ExpenseApprovalStep.StepStatus.PENDING,
            )
        except ExpenseApprovalStep.DoesNotExist:
            return Response(
                {'detail': 'BOT ratification step not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        with transaction.atomic():
            step.actor    = request.user
            step.note     = note
            step.acted_at = timezone.now()

            if action == 'approve':
                step.status    = ExpenseApprovalStep.StepStatus.APPROVED
                expense.status = ExpenseStatus.APPROVED
                next_step_msg  = 'Expense ratified by BOT and fully approved.'
            else:
                step.status    = ExpenseApprovalStep.StepStatus.REJECTED
                expense.status = ExpenseStatus.REJECTED
                next_step_msg  = 'Expense rejected by BOT.'

            step.save()
            expense.save()

        return Response({
            'detail':      f'BOT {action} action recorded.',
            'expense_ref': expense.expense_ref,
            'status':      expense.status,
            'next_step':   next_step_msg,
        })


@extend_schema(tags=['Expenses'])
class MarkExpensePaidView(APIView):
    """
    POST /api/v1/expenses/<id>/mark-paid/
    Treasurer or President marks an approved expense as paid.
    Generates payment record.
    """
    permission_classes = [IsTreasurerOrPresident]

    def post(self, request, pk):
        try:
            expense = Expense.objects.get(pk=pk)
        except Expense.DoesNotExist:
            return Response(
                {'detail': 'Expense not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if expense.status != ExpenseStatus.APPROVED:
            return Response(
                {'detail': 'Only approved expenses can be marked as paid.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = MarkPaidSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        expense.status      = ExpenseStatus.PAID
        expense.paid_at     = timezone.now()
        expense.paid_by     = request.user
        expense.payment_ref = serializer.validated_data['payment_ref']
        expense.save()

        return Response({
            'detail':       'Expense marked as paid.',
            'expense_ref':  expense.expense_ref,
            'amount_naira': expense.amount_naira,
            'paid_at':      expense.paid_at,
            'payment_ref':  expense.payment_ref,
        })


@extend_schema(tags=['Expenses'])
class BOTPendingExpensesView(generics.ListAPIView):
    """
    GET /api/v1/expenses/bot-pending/
    BOT members see all expenses awaiting their ratification.
    """
    serializer_class   = ExpenseListSerializer
    permission_classes = [IsBOTMember]

    def get_queryset(self):
        return Expense.objects.filter(
            status = ExpenseStatus.PENDING_BOT
        )


@extend_schema(tags=['Expenses'])
class ExpenseStatsView(APIView):
    """
    GET /api/v1/expenses/stats/
    ISCOOA Executive sees expense statistics.
    """
    permission_classes = [IsIscooaExec]

    def get(self, request):
        from django.db.models import Sum, Count

        expenses = Expense.objects.all()
        totals   = expenses.aggregate(
            total_amount = Sum('amount'),
            total_count  = Count('id'),
        )

        paid_total = Expense.objects.filter(
            status=ExpenseStatus.PAID
        ).aggregate(total=Sum('amount'))['total'] or 0

        return Response({
            'total_expenses':       totals['total_count'] or 0,
            'total_amount_naira':   (totals['total_amount'] or 0) / 100,
            'paid_amount_naira':    paid_total / 100,
            'by_status': {
                item['status']: item['count']
                for item in expenses.values('status').annotate(count=Count('id'))
            },
            'by_category': {
                item['category']: item['count']
                for item in expenses.values('category').annotate(count=Count('id'))
            },
            'bot_required_count': expenses.filter(requires_bot=True).count(),
        })