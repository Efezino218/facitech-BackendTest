from django.utils import timezone
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response

from django.utils import timezone
from django.db import transaction
from notifications.utils import send_notification, send_bulk_notification
from accounts.models import User


from .models import Penalty, ShutdownNotice
from .serializers import (
    PenaltySerializer, PenaltyCreateSerializer,
    ShutdownNoticeSerializer, ShutdownCreateSerializer,
)
from .permissions import IsOperator, IsIscooaExec
from drf_spectacular.utils import extend_schema


# ─── OPERATOR VIEWS ───────────────────────────────────────────────────────────

@extend_schema(tags=['Enforcement'])
class MyPenaltiesView(generics.ListAPIView):
    """
    GET /api/v1/enforcement/my-penalties/
    Operator sees all penalties against them.
    Filter by ?status=unpaid|paid|waived|disputed
    """
    serializer_class   = PenaltySerializer
    permission_classes = [IsOperator]

    def get_queryset(self):
        qs = Penalty.objects.filter(operator=self.request.user)
        pen_status = self.request.query_params.get('status')
        if pen_status:
            qs = qs.filter(status=pen_status)
        return qs


@extend_schema(tags=['Enforcement'])
class MyPenaltyDetailView(generics.RetrieveAPIView):
    """
    GET /api/v1/enforcement/my-penalties/<id>/
    Operator views a single penalty detail.
    """
    serializer_class   = PenaltySerializer
    permission_classes = [IsOperator]

    def get_queryset(self):
        return Penalty.objects.filter(operator=self.request.user)


@extend_schema(tags=['Enforcement'])
class MyShutdownsView(generics.ListAPIView):
    """
    GET /api/v1/enforcement/my-shutdowns/
    Operator sees all shutdown notices issued to them.
    Filter by ?status=active|lifted
    """
    serializer_class   = ShutdownNoticeSerializer
    permission_classes = [IsOperator]

    def get_queryset(self):
        qs = ShutdownNotice.objects.filter(
            operator = self.request.user
        )
        sdn_status = self.request.query_params.get('status')
        if sdn_status:
            qs = qs.filter(status=sdn_status)
        return qs


# ─── ISCOOA EXECUTIVE VIEWS ───────────────────────────────────────────────────

@extend_schema(tags=['Enforcement'])
class AllPenaltiesView(generics.ListAPIView):
    """
    GET /api/v1/enforcement/all-penalties/
    ISCOOA Executive sees all penalties.
    Filter by ?status=unpaid|paid|waived|disputed
    Filter by ?penalty_type=late_payment|unauthorized_signage etc
    """
    serializer_class   = PenaltySerializer
    permission_classes = [IsIscooaExec]

    def get_queryset(self):
        qs = Penalty.objects.filter(
            operator__association = self.request.user.association
        )
        pen_status = self.request.query_params.get('status')
        if pen_status:
            qs = qs.filter(status=pen_status)
        penalty_type = self.request.query_params.get('penalty_type')
        if penalty_type:
            qs = qs.filter(penalty_type=penalty_type)
        return qs


@extend_schema(tags=['Enforcement'])
class IssuePenaltyView(generics.CreateAPIView):
    """
    POST /api/v1/enforcement/issue-penalty/
    ISCOOA Executive issues a penalty notice.
    """
    serializer_class   = PenaltyCreateSerializer
    permission_classes = [IsIscooaExec]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        penalty = serializer.save(issued_by=request.user)

        # Send notification to operator
        # from notifications.utils import send_notification
        send_notification(
            user       = penalty.operator,
            category   = 'penalties',
            title      = f'Penalty Notice Issued — {penalty.penalty_ref}',
            message    = f'A penalty of ₦{penalty.amount_naira:,.2f} has been issued against your shop {penalty.shop.shop_number if penalty.shop else ""}. Reason: {penalty.get_penalty_type_display()}. Due date: {penalty.due_date}.',
            related_id = str(penalty.id),
        )

        return Response(
            {
                'detail':       'Penalty issued successfully.',
                'penalty_ref':  penalty.penalty_ref,
                'amount_naira': penalty.amount_naira,
                'due_date':     penalty.due_date,
                'status':       penalty.status,
            },
            status=status.HTTP_201_CREATED
        )


@extend_schema(tags=['Enforcement'])
class PenaltyDetailAdminView(generics.RetrieveAPIView):
    """
    GET /api/v1/enforcement/all-penalties/<id>/
    ISCOOA Executive views full penalty detail.
    """
    serializer_class   = PenaltySerializer
    permission_classes = [IsIscooaExec]

    def get_queryset(self):
        return Penalty.objects.filter(
            operator__association = self.request.user.association
        )


@extend_schema(tags=['Enforcement'])
class WaivePenaltyView(APIView):
    """
    POST /api/v1/enforcement/penalties/<id>/waive/
    ISCOOA Executive waives a penalty.
    """
    permission_classes = [IsIscooaExec]

    def post(self, request, pk):
        try:
            penalty = Penalty.objects.get(
                pk = pk,
                operator__association = request.user.association,
            )
        except Penalty.DoesNotExist:
            return Response(
                {'detail': 'Penalty not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if penalty.status not in [Penalty.Status.UNPAID, Penalty.Status.DISPUTED]:
            return Response(
                {'detail': f'Cannot waive a penalty with status {penalty.status}.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        waiver_reason = request.data.get('waiver_reason', '')
        if not waiver_reason:
            return Response(
                {'detail': 'A waiver reason is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        penalty.status        = Penalty.Status.WAIVED
        penalty.waived_by     = request.user
        penalty.waiver_reason = waiver_reason
        penalty.save()

        return Response({
            'detail':       'Penalty waived successfully.',
            'penalty_ref':  penalty.penalty_ref,
            'status':       penalty.status,
        })


@extend_schema(tags=['Enforcement'])
class AllShutdownsView(generics.ListAPIView):
    """
    GET /api/v1/enforcement/all-shutdowns/
    ISCOOA Executive sees all shutdown notices.
    Filter by ?status=active|lifted|pending
    """
    serializer_class   = ShutdownNoticeSerializer
    permission_classes = [IsIscooaExec]

    def get_queryset(self):
        qs = ShutdownNotice.objects.filter(
            operator__association = self.request.user.association
        )
        sdn_status = self.request.query_params.get('status')
        if sdn_status:
            qs = qs.filter(status=sdn_status)
        return qs


@extend_schema(tags=['Enforcement'])
class ShutdownDetailAdminView(generics.RetrieveAPIView):
    """
    GET /api/v1/enforcement/all-shutdowns/<id>/
    ISCOOA Executive views full shutdown detail with operator response.
    """
    serializer_class = ShutdownNoticeSerializer
    permission_classes = [IsIscooaExec]

    def get_queryset(self):
        return ShutdownNotice.objects.filter(
            operator__association=self.request.user.association
        )


@extend_schema(tags=['Enforcement'])
class IssueShutdownView(generics.CreateAPIView):
    """
    POST /api/v1/enforcement/issue-shutdown/
    ISCOOA Executive issues a shop shutdown notice.
    """
    serializer_class   = ShutdownCreateSerializer
    permission_classes = [IsIscooaExec]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        shutdown = serializer.save(
            issued_by = request.user,
            status    = ShutdownNotice.Status.ACTIVE,
        )

        # Send notification to operator
        # from notifications.utils import send_notification
        send_notification(
            user       = shutdown.operator,
            category   = 'penalties',
            title      = f'Shop Shutdown Notice — {shutdown.shutdown_ref}',
            message    = f'A shutdown notice has been issued for your shop {shutdown.shop.shop_number}. Reason: {shutdown.get_reason_display()}. Please contact ISCOOA immediately.',
            related_id = str(shutdown.id),
        )

        return Response(
            {
                'detail':        'Shutdown notice issued successfully.',
                'shutdown_ref':  shutdown.shutdown_ref,
                'shop':          shutdown.shop.shop_number,
                'reason':        shutdown.get_reason_display(),
                'status':        shutdown.status,
            },
            status=status.HTTP_201_CREATED
        )


@extend_schema(tags=['Enforcement'])
class LiftShutdownView(APIView):
    """
    POST /api/v1/enforcement/all-shutdowns/<id>/lift/
    ISCOOA Executive lifts a shutdown notice.
    A lift reason is required.
    Operator is notified immediately.
    """
    permission_classes = [IsIscooaExec]

    def post(self, request, pk):
        try:
            shutdown = ShutdownNotice.objects.get(
                pk                    = pk,
                operator__association = request.user.association,
            )
        except ShutdownNotice.DoesNotExist:
            return Response(
                {'detail': 'Shutdown notice not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if shutdown.status == 'lifted':
            return Response(
                {
                    'detail': (
                        f'This shutdown was already lifted on '
                        f'{shutdown.lifted_at.strftime("%d %b %Y") if shutdown.lifted_at else "an earlier date"}.'
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        lift_reason = request.data.get('reason', '').strip()
        if not lift_reason:
            return Response(
                {'detail': 'A lift reason is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        shutdown.status      = 'lifted'
        shutdown.lifted_by   = request.user
        shutdown.lifted_at   = timezone.now()
        shutdown.lift_reason = lift_reason
        shutdown.save()

        # Notify operator shutdown has been lifted
        send_notification(
            user       = shutdown.operator,
            category   = 'general',
            title      = f'Shutdown Lifted — {shutdown.shutdown_ref}',
            message    = (
                f'Your shop {shutdown.shop.shop_number} shutdown notice '
                f'({shutdown.shutdown_ref}) has been lifted by ISCOOA. '
                f'Reason: {lift_reason}. '
                f'You may resume normal operations immediately.'
            ),
            related_id = str(shutdown.id),
        )

        return Response({
            'detail':      'Shutdown lifted successfully. Operator has been notified.',
            'shutdown_ref':  shutdown.shutdown_ref,
            'status':      shutdown.status,
            'lift_reason': shutdown.lift_reason,
            'lifted_by':   request.user.full_name,
            'lifted_at':   shutdown.lifted_at,
        })


@extend_schema(tags=['Enforcement'])
class EnforcementStatsView(APIView):
    """
    GET /api/v1/enforcement/stats/
    ISCOOA Executive sees enforcement statistics.
    """
    permission_classes = [IsIscooaExec]

    def get(self, request):
        from django.db.models import Sum, Count

        penalties  = Penalty.objects.filter(
            operator__association = request.user.association
        )
        shutdowns  = ShutdownNotice.objects.filter(
            operator__association = request.user.association
        )

        pen_totals = penalties.aggregate(
            total_amount  = Sum('amount'),
            total_count   = Count('id'),
        )

        return Response({
            'penalties': {
                'total':            pen_totals['total_count'] or 0,
                'total_amount_naira': (pen_totals['total_amount'] or 0) / 100,
                'by_status': {
                    item['status']: item['count']
                    for item in penalties.values('status').annotate(count=Count('id'))
                },
            },
            'shutdowns': {
                'total':  shutdowns.count(),
                'active': shutdowns.filter(status='active').count(),
                'lifted': shutdowns.filter(status='lifted').count(),
            },
        })
    

@extend_schema(tags=['Enforcement'])
class RespondToPenaltyView(APIView):
    """
    POST /api/v1/enforcement/my-penalties/<id>/respond/
    Operator submits a written response to a penalty.
    This does not remove the penalty — it goes on record.
    Notifies issuing executive of the response.
    """
    permission_classes = [IsOperator]

    def post(self, request, pk):
        try:
            penalty = Penalty.objects.get(
                pk       = pk,
                operator = request.user,
            )
        except Penalty.DoesNotExist:
            return Response(
                {'detail': 'Penalty not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        response_text = request.data.get('response', '').strip()
        if not response_text:
            return Response(
                {'detail': 'A written response is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if penalty.operator_response:
            return Response(
                {'detail': 'You have already submitted a response to this penalty.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        penalty.operator_response    = response_text
        penalty.operator_responded_at = timezone.now()
        penalty.save()

        # Notify all association executives of the response
        exco_users = User.objects.filter(
            role        = 'is',
            association = request.user.association,
            is_active   = True,
        )
        send_bulk_notification(
            users      = exco_users,
            category   = 'general',
            title      = f'Penalty Response — {penalty.penalty_ref}',
            message    = (
                f'Operator {request.user.full_name or request.user.email} '
                f'has submitted a response to penalty {penalty.penalty_ref}. '
                f'Response: "{response_text[:100]}..."'
            ),
            related_id = str(penalty.id),
        )

        return Response({
            'detail':       'Your response has been recorded and sent to ISCOOA.',
            'penalty_ref':  penalty.penalty_ref,
            'response':     response_text,
            'responded_at': penalty.operator_responded_at,
        })


@extend_schema(tags=['Enforcement'])
class PayPenaltyFineView(APIView):
    """
    POST /api/v1/enforcement/my-penalties/<id>/pay-fine/
    Operator pays their penalty fine via Cool MFB wallet.
    Debits wallet, marks fine as paid, status becomes 'paid'.
    Fine goes 100% to the association.
    """
    permission_classes = [IsOperator]

    def post(self, request, pk):
        try:
            penalty = Penalty.objects.get(
                pk       = pk,
                operator = request.user,
            )
        except Penalty.DoesNotExist:
            return Response(
                {'detail': 'Penalty not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # ── Guard checks using correct field names ─────────────────────

        if not penalty.amount or penalty.amount == 0:
            return Response(
                {'detail': 'This penalty has no fine amount to pay.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if penalty.status == 'paid':
            return Response(
                {'detail': 'The fine for this penalty has already been paid.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if penalty.status == 'waived':
            return Response(
                {'detail': 'This penalty has been waived. No payment required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if penalty.fine_paid:
            return Response(
                {'detail': 'This fine has already been paid.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ── Get or create wallet ──────────────────────────────────────
        from wallet.models import Wallet
        wallet, _ = Wallet.objects.get_or_create(
            operator = request.user,
            defaults = {
                'balance':                0,
                'coolmfb_account_number': f"COOL{request.user.id.hex[:10].upper()}",
                'coolmfb_account_name':   request.user.full_name or request.user.email,
            }
        )

        if wallet.balance < penalty.amount:
            return Response(
                {
                    'detail': (
                        f'Insufficient wallet balance. '
                        f'Fine amount: ₦{penalty.amount/100:,.2f}. '
                        f'Available: ₦{wallet.balance_naira:,.2f}. '
                        f'Please top up your wallet.'
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            payment_ref = (
                f"FINE-{penalty.penalty_ref}-"
                f"{timezone.now().strftime('%Y%m%d%H%M%S')}"
            )

            # ── Debit wallet ──────────────────────────────────────────
            try:
                wallet.debit(
                    amount_kobo = penalty.amount,
                    description = (
                        f'Penalty fine — {penalty.penalty_ref}: '
                        f'{penalty.description[:50]}'   # ← correct field
                    ),
                    method = 'wallet',
                    ref    = payment_ref,
                )
            except ValueError as e:
                return Response(
                    {'detail': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # ── Update penalty status ─────────────────────────────────
            penalty.fine_paid        = True
            penalty.fine_paid_at     = timezone.now()
            penalty.fine_payment_ref = payment_ref
            penalty.status           = 'paid'     # ← update status to paid
            penalty.save()

            # ── Distribute fine revenue 100% to association ───────────
            try:
                from revenue.utils import distribute_revenue
                from revenue.models import RevenueDistribution
                distribute_revenue(
                    association           = request.user.association,
                    operator              = request.user,
                    total_amount_kobo     = penalty.amount,
                    payment_type          = RevenueDistribution.PaymentType.BILL,
                    source_ref            = payment_ref,
                    association_share_pct = 100,
                    platform_share_pct    = 0,
                    note                  = (
                        f'Penalty fine — {penalty.penalty_ref}'
                    ),
                )
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(
                    f'Revenue distribution failed for penalty fine {payment_ref}: {e}'
                )

        # ── Notify Treasurer ──────────────────────────────────────────
        treasurer_users = User.objects.filter(
            role        = 'is',
            ipos        = 'treasurer',
            association = request.user.association,
            is_active   = True,
        )
        send_bulk_notification(
            users      = treasurer_users,
            category   = 'general',
            title      = f'Penalty Fine Paid — {penalty.penalty_ref}',
            message    = (
                f'Operator {request.user.full_name or request.user.email} '
                f'has paid the fine of ₦{penalty.amount/100:,.2f} '
                f'for penalty {penalty.penalty_ref}. '
                f'Payment ref: {payment_ref}.'
            ),
            related_id = str(penalty.id),
        )

        return Response({
            'detail':                   'Fine paid successfully.',
            'penalty_ref':              penalty.penalty_ref,
            'status':                   penalty.status,
            'fine_amount_naira':        penalty.amount / 100,
            'payment_ref':              payment_ref,
            'new_wallet_balance_naira': wallet.balance_naira,
        })


@extend_schema(tags=['Enforcement'])
class RespondToShutdownView(APIView):
    """
    POST /api/v1/enforcement/my-shutdowns/<id>/respond/
    Operator submits a formal written response to a shutdown notice.
    Notifies all ISCOOA executives of the response.
    Only one response allowed per shutdown notice.
    """
    permission_classes = [IsOperator]

    def post(self, request, pk):
        try:
            shutdown = ShutdownNotice.objects.get(
                pk       = pk,
                operator = request.user,
            )
        except ShutdownNotice.DoesNotExist:
            return Response(
                {'detail': 'Shutdown notice not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if shutdown.status == 'lifted':
            return Response(
                {'detail': 'This shutdown has already been lifted. No response needed.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if shutdown.operator_response:
            return Response(
                {
                    'detail': 'You have already submitted a response to this shutdown notice.',
                    'responded_at': shutdown.operator_responded_at,
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        response_text = request.data.get('response', '').strip()
        if not response_text:
            return Response(
                {'detail': 'A written response is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        shutdown.operator_response     = response_text
        shutdown.operator_responded_at = timezone.now()
        shutdown.save()

        # Notify all ISCOOA executives
        exco_users = User.objects.filter(
            role        = 'is',
            association = request.user.association,
            is_active   = True,
        )
        send_bulk_notification(
            users      = exco_users,
            category   = 'general',
            title      = f'Shutdown Response — {shutdown.shutdown_ref}',
            message    = (
                f'Operator {request.user.full_name or request.user.email} '
                f'has submitted a response to shutdown notice {shutdown.shutdown_ref}: '
                f'"{response_text[:120]}"'
            ),
            related_id = str(shutdown.id),
        )

        return Response({
            'detail':       'Your response has been submitted to ISCOOA.',
            'shutdown_ref':   shutdown.shutdown_ref,
            'response':     response_text,
            'responded_at': shutdown.operator_responded_at,
        })


@extend_schema(tags=['Enforcement'])
class AcknowledgePenaltyResponseView(APIView):
    """
    POST /api/v1/enforcement/all-penalties/<id>/acknowledge-response/
    Executive reviews operator response and takes action.
    action: "waive"  → status = waived, fine cancelled
    action: "uphold" → status = disputed, fine remains payable
    Once actioned the penalty is locked — no further actions.
    """
    permission_classes = [IsIscooaExec]

    def post(self, request, pk):
        try:
            penalty = Penalty.objects.get(
                pk                    = pk,
                operator__association = request.user.association,
            )
        except Penalty.DoesNotExist:
            return Response(
                {'detail': 'Penalty not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # ── Lock check — correct field names ──────────────────────────
        if penalty.status == 'waived':
            return Response(
                {
                    'detail': (
                        f'This penalty has already been waived. '
                        f'Reason: {penalty.waiver_reason or "No reason recorded"}.'
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if penalty.status == 'disputed':
            return Response(
                {'detail': 'This penalty has already been upheld and is locked.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if penalty.status == 'paid':
            return Response(
                {'detail': 'This penalty fine has already been paid. No further action needed.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ── Response check ─────────────────────────────────────────────
        if not penalty.operator_response:
            return Response(
                {'detail': 'Operator has not submitted a response yet.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ── Validate input ─────────────────────────────────────────────
        action = request.data.get('action', '').lower().strip()
        note   = request.data.get('note', '').strip()

        if action not in ['uphold', 'waive']:
            return Response(
                {'detail': 'action must be either "uphold" or "waive".'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not note:
            return Response(
                {'detail': 'A note is required for both uphold and waive actions.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        from notifications.utils import send_notification

        if action == 'waive':
            # ── Waive the penalty ──────────────────────────────────────
            penalty.status        = 'waived'          # ← correct field
            penalty.waiver_reason = note              # ← correct field
            penalty.waived_by     = request.user
            penalty.waived_at     = timezone.now()
            penalty.save()

            send_notification(
                user       = penalty.operator,
                category   = 'general',
                title      = f'Penalty Waived — {penalty.penalty_ref}',
                message    = (
                    f'After reviewing your response, ISCOOA has waived '
                    f'penalty {penalty.penalty_ref}. '
                    f'Note: {note}'
                ),
                related_id = str(penalty.id),
            )

            return Response({
                'detail':        'Penalty waived successfully.',
                'penalty_ref':   penalty.penalty_ref,
                'status':        penalty.status,
                'waiver_reason': penalty.waiver_reason,
                'waived_by':     request.user.full_name,
                'waived_at':     penalty.waived_at,
            })

        else:
            # ── Uphold the penalty ─────────────────────────────────────
            penalty.status        = 'disputed'        # ← locks the penalty
            penalty.waiver_reason = f'[Upheld] {note}'
            penalty.save()

            send_notification(
                user       = penalty.operator,
                category   = 'general',
                title      = f'Penalty Upheld — {penalty.penalty_ref}',
                message    = (
                    f'ISCOOA has reviewed your response and upheld '
                    f'penalty {penalty.penalty_ref}. '
                    f'Note: {note}. '
                    + (
                        f'Fine of ₦{penalty.amount/100:,.2f} remains payable.'
                        if penalty.amount and not penalty.fine_paid
                        else ''
                    )
                ),
                related_id = str(penalty.id),
            )

            return Response({
                'detail':            'Penalty upheld. Operator has been notified.',
                'penalty_ref':       penalty.penalty_ref,
                'status':            penalty.status,
                'uphold_note':       note,
                'upheld_by':         request.user.full_name,
                'fine_still_payable': (
                    penalty.amount > 0 and not penalty.fine_paid
                    if penalty.amount else False
                ),
            })