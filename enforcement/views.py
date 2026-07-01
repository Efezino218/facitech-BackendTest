from django.utils import timezone
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response

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
    Operator sees all shutdown notices against their shops.
    Filter by ?status=active|lifted|pending
    """
    serializer_class   = ShutdownNoticeSerializer
    permission_classes = [IsOperator]

    def get_queryset(self):
        qs = ShutdownNotice.objects.filter(operator=self.request.user)
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
        from notifications.utils import send_notification
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
        from notifications.utils import send_notification
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
    POST /api/v1/enforcement/shutdowns/<id>/lift/
    ISCOOA Executive lifts a shutdown notice.
    Notifies operator and HFP.
    """
    permission_classes = [IsIscooaExec]

    def post(self, request, pk):
        try:
            shutdown = ShutdownNotice.objects.get(
                pk = pk,
                operator__association = request.user.association,
            )
        except ShutdownNotice.DoesNotExist:
            return Response(
                {'detail': 'Shutdown notice not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if shutdown.status == ShutdownNotice.Status.LIFTED:
            return Response(
                {'detail': 'This shutdown has already been lifted.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        lift_reason = request.data.get('lift_reason', '')
        if not lift_reason:
            return Response(
                {'detail': 'A lift reason is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        shutdown.status      = ShutdownNotice.Status.LIFTED
        shutdown.lifted_at   = timezone.now()
        shutdown.lifted_by   = request.user
        shutdown.lift_reason = lift_reason
        shutdown.save()

        # Notify operator
        from notifications.utils import send_notification
        send_notification(
            user       = shutdown.operator,
            category   = 'penalties',
            title      = f'Shutdown Lifted — {shutdown.shutdown_ref}',
            message    = f'The shutdown notice on your shop {shutdown.shop.shop_number} has been lifted. Reason: {lift_reason}. You may resume normal trading.',
            related_id = str(shutdown.id),
        )

        return Response({
            'detail':       'Shutdown lifted successfully.',
            'shutdown_ref': shutdown.shutdown_ref,
            'lifted_at':    shutdown.lifted_at,
            'lift_reason':  shutdown.lift_reason,
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