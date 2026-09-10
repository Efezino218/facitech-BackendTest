from django.utils import timezone
from django.db import transaction
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from drf_spectacular.utils import extend_schema

from .models import Expense, ExpenseApprovalStep, ExpenseStatus
from .serializers import ExpenseSerializer, ExpenseListSerializer
from .permissions import IsIscooaExec, IsTreasurer, IsBOTChairman, IsBOTMember


def create_approval_steps(expense):
    """Create the approval chain for an expense."""
    steps = [
        {'role': 'treasurer',        'step_number': 1},
        {'role': 'secretary_general', 'step_number': 2},
        {'role': 'president',         'step_number': 3},
    ]
    for step in steps:
        ExpenseApprovalStep.objects.create(
            expense     = expense,
            role        = step['role'],
            step_number = step['step_number'], 
        )


@extend_schema(tags=['Expenses'])
class RaiseExpenseView(APIView):
    """
    POST /api/v1/expenses/raise/
    ISCOOA Executive raises a new expense.
    Expense above BOT threshold goes to BOT after President approval.
    """
    permission_classes = [IsIscooaExec]

    def post(self, request):
        from .serializers import ExpenseCreateSerializer
        serializer = ExpenseCreateSerializer(
            data=request.data,
            context={'request': request}
        )
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            expense = serializer.save(
                raised_by   = request.user,
                association = request.user.association,
                status      = ExpenseStatus.PENDING_TREASURER,
            )
            create_approval_steps(expense)

            # Notify Treasurer
            from notifications.utils import send_bulk_notification
            from accounts.models import User
            treasurer_users = User.objects.filter(
                role        = 'is',
                ipos        = 'treasurer',
                association = request.user.association,
                is_active   = True,
            )
            send_bulk_notification(
                users      = treasurer_users,
                category   = 'expenses',
                title      = f'New Expense Awaiting Approval — {expense.expense_ref}',
                message    = (
                    f'{request.user.full_name} raised expense '
                    f'{expense.expense_ref}: "{expense.title}" — '
                    f'₦{expense.amount_naira:,.2f}. '
                    f'Awaiting your approval.'
                    + (' ⚠️ HIGH VALUE — BOT ratification required after President approval.'
                       if expense.requires_bot else '')
                ),
                related_id = str(expense.id),
            )

        return Response(
            ExpenseSerializer(expense).data,
            status=status.HTTP_201_CREATED
        )


@extend_schema(tags=['Expenses'])
class AllExpensesView(generics.ListAPIView):
    """
    GET /api/v1/expenses/
    ISCOOA Executive sees all expenses for their association.
    Filter by ?status=pending_treasurer|pending_secretary|pending_president|pending_bot|approved|paid|rejected|deferred
    """
    serializer_class   = ExpenseListSerializer
    permission_classes = [IsIscooaExec]

    def get_queryset(self):
        qs = Expense.objects.filter(
            association=self.request.user.association
        )
        exp_status = self.request.query_params.get('status')
        if exp_status:
            qs = qs.filter(status=exp_status)
        return qs.order_by('-created_at')


@extend_schema(tags=['Expenses'])
class ExpenseDetailView(generics.RetrieveAPIView):
    """
    GET /api/v1/expenses/<id>/
    ISCOOA Executive views full expense detail.
    """
    serializer_class   = ExpenseSerializer
    permission_classes = [IsIscooaExec]

    def get_queryset(self):
        return Expense.objects.filter(
            association=self.request.user.association
        )


@extend_schema(tags=['Expenses'])
class ApproveExpenseStepView(APIView):
    """
    POST /api/v1/expenses/<id>/action/
    Treasurer, Secretary General, or President acts on an expense.
    Each role can only act when it is their turn in the chain.
    action: approve or reject
    """
    permission_classes = [IsIscooaExec]

    def post(self, request, pk):
        try:
            expense = Expense.objects.get(
                pk          = pk,
                association = request.user.association,
            )
        except Expense.DoesNotExist:
            return Response(
                {'detail': 'Expense not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        user_ipos = request.user.ipos
        note      = request.data.get('note', '')
        action    = request.data.get('action', '').lower()

        if action not in ['approve', 'reject']:
            return Response(
                {'detail': 'action must be approve or reject.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ── Check it is this user's turn ──────────────────────────────
        turn_map = {
            'treasurer':         ExpenseStatus.PENDING_TREASURER,
            'secretary_general': ExpenseStatus.PENDING_SECRETARY,
            'president':         ExpenseStatus.PENDING_PRESIDENT,
        }
        expected_status = turn_map.get(user_ipos)

        if not expected_status:
            return Response(
                {'detail': 'Your role is not part of the expense approval chain.'},
                status=status.HTTP_403_FORBIDDEN
            )

        if expense.status != expected_status:
            return Response(
                {
                    'detail': (
                        f'This expense is not awaiting your approval. '
                        f'Current status: {expense.status}.'
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        from notifications.utils import send_notification, send_bulk_notification
        from accounts.models import User

        with transaction.atomic():
            # Get or create the step record for this role
            step, _ = ExpenseApprovalStep.objects.get_or_create(
                expense = expense,
                role    = user_ipos,
            )
            step.actioned_by = request.user
            step.actioned_at = timezone.now()
            step.note        = note

            if action == 'approve':
                step.status = 'approved'
                step.save()

                if user_ipos == 'treasurer':
                    expense.status = ExpenseStatus.PENDING_SECRETARY

                    # Notify Secretary General
                    sec_users = User.objects.filter(
                        role='is', ipos='secretary_general',
                        association=expense.association, is_active=True,
                    )
                    send_bulk_notification(
                        users      = sec_users,
                        category   = 'expenses',
                        title      = f'Expense Awaiting Your Approval — {expense.expense_ref}',
                        message    = (
                            f'Expense {expense.expense_ref} "{expense.title}" '
                            f'(₦{expense.amount_naira:,.2f}) approved by Treasurer. '
                            f'Awaiting your review.'
                        ),
                        related_id = str(expense.id),
                    )

                elif user_ipos == 'secretary_general':
                    expense.status = ExpenseStatus.PENDING_PRESIDENT

                    # Notify President
                    pres_users = User.objects.filter(
                        role='is', ipos='president',
                        association=expense.association, is_active=True,
                    )
                    send_bulk_notification(
                        users      = pres_users,
                        category   = 'expenses',
                        title      = f'Expense Awaiting Your Approval — {expense.expense_ref}',
                        message    = (
                            f'Expense {expense.expense_ref} "{expense.title}" '
                            f'(₦{expense.amount_naira:,.2f}) approved by Secretary General. '
                            f'Awaiting your final approval.'
                        ),
                        related_id = str(expense.id),
                    )

                elif user_ipos == 'president':
                    if expense.requires_bot:
                        # HIGH VALUE — send to BOT for ratification
                        expense.status = ExpenseStatus.PENDING_BOT

                        # Notify ALL BOT members
                        bot_users = User.objects.filter(
                            role        = 'bot',
                            association = expense.association,
                            is_active   = True,
                        )
                        send_bulk_notification(
                            users      = bot_users,
                            category   = 'expenses',
                            title      = f'High-Value Expense Requires BOT Ratification — {expense.expense_ref}',
                            message    = (
                                f'Expense {expense.expense_ref} "{expense.title}" '
                                f'(₦{expense.amount_naira:,.2f}) has been approved by all '
                                f'executives. Requires BOT Chairman ratification. '
                                f'Only the BOT Chairman can ratify, defer or reject.'
                            ),
                            related_id = str(expense.id),
                        )
                    else:
                        # NORMAL VALUE — fully approved
                        expense.status = ExpenseStatus.APPROVED

                        # Notify Treasurer to make payment
                        treasurer_users = User.objects.filter(
                            role='is', ipos='treasurer',
                            association=expense.association, is_active=True,
                        )
                        send_bulk_notification(
                            users      = treasurer_users,
                            category   = 'expenses',
                            title      = f'Expense Fully Approved — {expense.expense_ref}',
                            message    = (
                                f'Expense {expense.expense_ref} "{expense.title}" '
                                f'(₦{expense.amount_naira:,.2f}) has been fully approved '
                                f'by the President. Please process payment and upload evidence.'
                            ),
                            related_id = str(expense.id),
                        )
                        # Also notify the raiser
                        send_notification(
                            user       = expense.raised_by,
                            category   = 'expenses',
                            title      = f'Expense Approved — {expense.expense_ref}',
                            message    = (
                                f'Your expense {expense.expense_ref} "{expense.title}" '
                                f'has been fully approved. '
                                f'Treasurer will process payment shortly.'
                            ),
                            related_id = str(expense.id),
                        )

                expense.save()

                return Response({
                    'detail':  f'Expense approved by {request.user.get_ipos_display()}.',
                    'expense_ref': expense.expense_ref,
                    'status':  expense.status,
                    'next_step': _get_next_step_description(expense),
                })

            else:  # reject
                if not note:
                    return Response(
                        {'detail': 'A rejection note is required.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                step.status = 'rejected'
                step.save()
                expense.status = ExpenseStatus.REJECTED
                expense.save()

                # Notify raiser
                send_notification(
                    user       = expense.raised_by,
                    category   = 'expenses',
                    title      = f'Expense Rejected — {expense.expense_ref}',
                    message    = (
                        f'Your expense {expense.expense_ref} "{expense.title}" '
                        f'was rejected by {request.user.get_ipos_display()}. '
                        f'Reason: {note}'
                    ),
                    related_id = str(expense.id),
                )

                return Response({
                    'detail':      f'Expense rejected by {request.user.get_ipos_display()}.',
                    'expense_ref': expense.expense_ref,
                    'status':      expense.status,
                    'note':        note,
                })


@extend_schema(tags=['Expenses'])
class BOTPendingExpensesView(generics.ListAPIView):
    """
    GET /api/v1/expenses/bot-pending/
    ALL BOT members (chairman and regular) can VIEW
    expenses pending BOT ratification.
    Only BOT Chairman can take action on them.
    """
    serializer_class   = ExpenseListSerializer
    permission_classes = [IsBOTMember]

    def get_queryset(self):
        return Expense.objects.filter(
            status      = ExpenseStatus.PENDING_BOT,
            association = self.request.user.association,
        ).order_by('-created_at')


@extend_schema(tags=['Expenses'])
class BOTAllExpensesView(generics.ListAPIView):
    """
    GET /api/v1/expenses/bot-all/
    ALL BOT members can view all expenses
    regardless of status — read only overview.
    """
    serializer_class   = ExpenseListSerializer
    permission_classes = [IsBOTMember]

    def get_queryset(self):
        qs = Expense.objects.filter(
            association=self.request.user.association
        )
        exp_status = self.request.query_params.get('status')
        if exp_status:
            qs = qs.filter(status=exp_status)
        return qs.order_by('-created_at')


@extend_schema(tags=['Expenses'])
class BOTRatifyExpenseView(APIView):
    """
    POST /api/v1/expenses/<id>/bot-action/
    BOT CHAIRMAN ONLY — can ratify, defer or reject.
    Regular BOT members cannot take any action here.

    action choices:
      approve — Ratify and approve. Expense moves to APPROVED.
      defer   — Defer to next BOT meeting. Status becomes DEFERRED.
                Expense can be re-submitted for BOT review later.
      reject  — BOT rejects the expense. Flow ends.

    All actions require a resolution_note.
    """
    permission_classes = [IsBOTChairman]

    def post(self, request, pk):
        try:
            expense = Expense.objects.get(
                pk          = pk,
                association = request.user.association,
            )
        except Expense.DoesNotExist:
            return Response(
                {'detail': 'Expense not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if expense.status != ExpenseStatus.PENDING_BOT:
            return Response(
                {
                    'detail': (
                        f'This expense is not pending BOT ratification. '
                        f'Current status: {expense.status}.'
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        action          = request.data.get('action', '').lower()
        resolution_note = request.data.get('resolution_note', '').strip()

        if action not in ['approve', 'defer', 'reject']:
            return Response(
                {'detail': 'action must be approve, defer or reject.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not resolution_note:
            return Response(
                {'detail': 'A resolution note is required for all BOT actions.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        from notifications.utils import send_notification, send_bulk_notification
        from accounts.models import User

        with transaction.atomic():
            expense.bot_resolution_note = resolution_note
            expense.bot_actioned_by     = request.user
            expense.bot_actioned_at     = timezone.now()

            if action == 'approve':
                expense.status = ExpenseStatus.APPROVED

                # Notify Treasurer to process payment
                treasurer_users = User.objects.filter(
                    role='is', ipos='treasurer',
                    association=expense.association, is_active=True,
                )
                send_bulk_notification(
                    users      = treasurer_users,
                    category   = 'expenses',
                    title      = f'Expense Ratified by BOT — {expense.expense_ref}',
                    message    = (
                        f'Expense {expense.expense_ref} "{expense.title}" '
                        f'(₦{expense.amount_naira:,.2f}) has been ratified by the '
                        f'BOT Chairman. Please process payment and upload evidence. '
                        f'BOT resolution: {resolution_note}'
                    ),
                    related_id = str(expense.id),
                )
                # Notify raiser
                send_notification(
                    user       = expense.raised_by,
                    category   = 'expenses',
                    title      = f'Expense Ratified — {expense.expense_ref}',
                    message    = (
                        f'Your expense {expense.expense_ref} has been ratified '
                        f'by the BOT and is fully approved. '
                        f'Treasurer will process payment.'
                    ),
                    related_id = str(expense.id),
                )
                detail_msg = 'Expense ratified and approved by BOT Chairman.'

            elif action == 'defer':
                expense.status = ExpenseStatus.DEFERRED

                # Notify all executives
                exco_users = User.objects.filter(
                    role='is', association=expense.association, is_active=True,
                )
                send_bulk_notification(
                    users      = exco_users,
                    category   = 'expenses',
                    title      = f'Expense Deferred — {expense.expense_ref}',
                    message    = (
                        f'Expense {expense.expense_ref} "{expense.title}" '
                        f'(₦{expense.amount_naira:,.2f}) has been deferred to the '
                        f'next BOT meeting. '
                        f'Reason: {resolution_note}'
                    ),
                    related_id = str(expense.id),
                )
                # Notify raiser
                send_notification(
                    user       = expense.raised_by,
                    category   = 'expenses',
                    title      = f'Expense Deferred — {expense.expense_ref}',
                    message    = (
                        f'Your expense {expense.expense_ref} has been deferred '
                        f'to the next BOT meeting. '
                        f'Reason: {resolution_note}'
                    ),
                    related_id = str(expense.id),
                )
                detail_msg = 'Expense deferred to next BOT meeting.'

            else:  # reject
                expense.status = ExpenseStatus.REJECTED

                send_notification(
                    user       = expense.raised_by,
                    category   = 'expenses',
                    title      = f'Expense Rejected by BOT — {expense.expense_ref}',
                    message    = (
                        f'Your expense {expense.expense_ref} "{expense.title}" '
                        f'has been rejected by the BOT. '
                        f'Resolution: {resolution_note}'
                    ),
                    related_id = str(expense.id),
                )
                detail_msg = 'Expense rejected by BOT Chairman.'

            expense.save()

        return Response({
            'detail':          detail_msg,
            'expense_ref':     expense.expense_ref,
            'status':          expense.status,
            'action':          action,
            'resolution_note': resolution_note,
            'actioned_by':     request.user.full_name,
            'next_step':       _get_next_step_description(expense),
        })


@extend_schema(tags=['Expenses'])
class MarkExpensePaidView(APIView):
    """
    POST /api/v1/expenses/<id>/mark-paid/
    Treasurer marks an approved expense as paid.
    Uploads payment evidence and records payment reference.
    This is the final step — the money has been physically paid.
    """
    permission_classes = [IsTreasurer]
    parser_classes     = [MultiPartParser, FormParser]

    def post(self, request, pk):
        try:
            expense = Expense.objects.get(
                pk          = pk,
                association = request.user.association,
            )
        except Expense.DoesNotExist:
            return Response(
                {'detail': 'Expense not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if expense.status != ExpenseStatus.APPROVED:
            return Response(
                {
                    'detail': (
                        f'Only approved expenses can be marked as paid. '
                        f'Current status: {expense.status}.'
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        payment_ref = request.data.get('payment_ref', '').strip()
        if not payment_ref:
            return Response(
                {'detail': 'A payment reference is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        evidence_file = request.FILES.get('payment_evidence')

        expense.status           = ExpenseStatus.PAID
        expense.payment_ref      = payment_ref
        expense.paid_by          = request.user
        expense.paid_at          = timezone.now()
        if evidence_file:
            expense.payment_evidence = evidence_file
        expense.save()

        # Notify raiser that payment has been made
        from notifications.utils import send_notification
        send_notification(
            user       = expense.raised_by,
            category   = 'expenses',
            title      = f'Expense Paid — {expense.expense_ref}',
            message    = (
                f'Expense {expense.expense_ref} "{expense.title}" '
                f'(₦{expense.amount_naira:,.2f}) has been paid. '
                f'Payment reference: {payment_ref}.'
            ),
            related_id = str(expense.id),
        )

        return Response({
            'detail':          'Expense marked as paid.',
            'expense_ref':     expense.expense_ref,
            'status':          expense.status,
            'payment_ref':     expense.payment_ref,
            'paid_by':         request.user.full_name,
            'paid_at':         expense.paid_at,
            'evidence_saved':  bool(evidence_file),
        })


@extend_schema(tags=['Expenses'])
class ResubmitDeferredExpenseView(APIView):
    """
    POST /api/v1/expenses/<id>/resubmit-to-bot/
    Treasurer resubmits a deferred expense to BOT.
    Used when BOT deferred to next meeting.
    Expense goes back to PENDING_BOT status.
    """
    permission_classes = [IsTreasurer]

    def post(self, request, pk):
        try:
            expense = Expense.objects.get(
                pk          = pk,
                association = request.user.association,
            )
        except Expense.DoesNotExist:
            return Response(
                {'detail': 'Expense not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if expense.status != ExpenseStatus.DEFERRED:
            return Response(
                {
                    'detail': (
                        f'Only deferred expenses can be resubmitted to BOT. '
                        f'Current status: {expense.status}.'
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        expense.status              = ExpenseStatus.PENDING_BOT
        expense.bot_resolution_note = ''
        expense.bot_actioned_by     = None
        expense.bot_actioned_at     = None
        expense.save()

        # Notify BOT members
        from notifications.utils import send_bulk_notification
        from accounts.models import User
        bot_users = User.objects.filter(
            role        = 'bot',
            association = request.user.association,
            is_active   = True,
        )
        send_bulk_notification(
            users      = bot_users,
            category   = 'expenses',
            title      = f'Deferred Expense Resubmitted — {expense.expense_ref}',
            message    = (
                f'Expense {expense.expense_ref} "{expense.title}" '
                f'(₦{expense.amount_naira:,.2f}) has been resubmitted '
                f'to BOT for ratification at the next meeting.'
            ),
            related_id = str(expense.id),
        )

        return Response({
            'detail':      'Expense resubmitted to BOT for ratification.',
            'expense_ref': expense.expense_ref,
            'status':      expense.status,
        })


@extend_schema(tags=['Expenses'])
class ExpenseStatsView(APIView):
    """
    GET /api/v1/expenses/stats/
    Association expense statistics for the dashboard.
    """
    permission_classes = [IsIscooaExec]

    def get(self, request):
        from django.db.models import Sum, Count
        expenses = Expense.objects.filter(
            association=request.user.association
        )

        total_count    = expenses.count()
        approved_count = expenses.filter(status=ExpenseStatus.APPROVED).count()
        paid_count     = expenses.filter(status=ExpenseStatus.PAID).count()
        pending_count  = expenses.exclude(
            status__in=[
                ExpenseStatus.APPROVED,
                ExpenseStatus.PAID,
                ExpenseStatus.REJECTED,
                ExpenseStatus.DEFERRED,
            ]
        ).count()
        bot_pending    = expenses.filter(status=ExpenseStatus.PENDING_BOT).count()
        deferred_count = expenses.filter(status=ExpenseStatus.DEFERRED).count()
        rejected_count = expenses.filter(status=ExpenseStatus.REJECTED).count()

        total_paid_naira = expenses.filter(
            status=ExpenseStatus.PAID
        ).aggregate(total=Sum('amount'))['total'] or 0

        return Response({
            'total_expenses':    total_count,
            'pending_approval':  pending_count,
            'pending_bot':       bot_pending,
            'approved':          approved_count,
            'deferred':          deferred_count,
            'paid':              paid_count,
            'rejected':          rejected_count,
            'total_paid_naira':  total_paid_naira / 100,
        })


def _get_next_step_description(expense):
    """Return a human-readable description of what happens next."""
    descriptions = {
        ExpenseStatus.PENDING_TREASURER:  'Awaiting Treasurer approval.',
        ExpenseStatus.PENDING_SECRETARY:  'Awaiting Secretary General approval.',
        ExpenseStatus.PENDING_PRESIDENT:  'Awaiting President final approval.',
        ExpenseStatus.PENDING_BOT:        'Awaiting BOT Chairman ratification. BOT Chairman can approve, defer or reject.',
        ExpenseStatus.APPROVED:           'Approved. Treasurer should process payment and mark as paid.',
        ExpenseStatus.DEFERRED:           'Deferred to next BOT meeting. Treasurer can resubmit when ready.',
        ExpenseStatus.REJECTED:           'Rejected. No further action.',
        ExpenseStatus.PAID:               'Paid. Flow complete.',
    }
    return descriptions.get(expense.status, '')