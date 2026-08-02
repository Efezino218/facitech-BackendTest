from django.db.models import Sum, Count
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from django.db import transaction as db_transaction
from .models import WithdrawalRequest
from .serializers import (
    WithdrawalRequestSerializer,
    WithdrawalRequestCreateSerializer,
    ProcessWithdrawalSerializer,
)

from .models import (
    RevenueWallet, RevenueTransaction,
    RevenueDistribution, RevenueWalletType,
)
from .serializers import (
    RevenueWalletSerializer, RevenueWalletSummarySerializer,
    RevenueTransactionSerializer, RevenueDistributionSerializer,
)
from .utils import get_or_create_association_wallet, get_or_create_platform_wallet
from .permissions import (
    IsTreasurer, IsPresident, IsSuperAdmin,
    IsTreasurerOrPresident,
)


@extend_schema(tags=['Revenue'])
class AssociationRevenueDashboardView(APIView):
    """
    GET /api/v1/revenue/association/dashboard/
    Treasurer and President see their association's
    full revenue dashboard.

    Shows:
    - Total balance available for withdrawal
    - Total ever earned
    - Total ever withdrawn
    - Breakdown by payment type
    - Recent transactions
    - Month-by-month summary
    """
    permission_classes = [IsTreasurerOrPresident]

    def get(self, request):
        assoc  = request.user.association
        wallet = get_or_create_association_wallet(assoc)

        # Revenue breakdown by payment type
        distributions = RevenueDistribution.objects.filter(
            association = assoc
        )

        by_type = {}
        for pt in RevenueDistribution.PaymentType.choices:
            code, label = pt
            total = distributions.filter(
                payment_type=code
            ).aggregate(total=Sum('association_amount'))['total'] or 0
            count = distributions.filter(payment_type=code).count()
            by_type[code] = {
                'label':       label,
                'total_naira': total / 100,
                'count':       count,
            }

        # This month's revenue
        month_str  = timezone.now().strftime('%Y-%m')
        this_month = distributions.filter(
            created_at__year  = timezone.now().year,
            created_at__month = timezone.now().month,
        ).aggregate(total=Sum('association_amount'))['total'] or 0

        # Last 10 transactions
        recent_txns = wallet.transactions.all()[:10]

        # Monthly breakdown for the last 6 months
        monthly = []
        from dateutil.relativedelta import relativedelta
        for i in range(5, -1, -1):
            month_date  = timezone.now() - relativedelta(months=i)
            month_total = distributions.filter(
                created_at__year  = month_date.year,
                created_at__month = month_date.month,
            ).aggregate(total=Sum('association_amount'))['total'] or 0
            monthly.append({
                'month':       month_date.strftime('%Y-%m'),
                'label':       month_date.strftime('%b %Y'),
                'total_naira': month_total / 100,
            })

        # Get split percentages from config
        try:
            config = assoc.config
            sub_assoc_pct  = config.association_share
            sub_plat_pct   = config.platform_share
            bill_assoc_pct = config.bill_association_share
            bill_plat_pct  = config.bill_platform_share
        except Exception:
            sub_assoc_pct  = 20
            sub_plat_pct   = 80
            bill_assoc_pct = 80
            bill_plat_pct  = 20

        return Response({
            'association':  assoc.name,
            'wallet': {
                'balance_naira':               wallet.balance_naira,
                'total_earned_naira':          wallet.total_earned_naira,
                'total_withdrawn_naira':       wallet.total_withdrawn_naira,
                'available_to_withdraw_naira': wallet.balance_naira,
            },
            'revenue_split_info': {
                'subscriptions_and_adverts': {
                    'association_pct': sub_assoc_pct,
                    'platform_pct':    sub_plat_pct,
                    'note': 'Platform revenue — Iprolance takes the larger share',
                },
                'bills_and_external_payments': {
                    'association_pct': bill_assoc_pct,
                    'platform_pct':    bill_plat_pct,
                    'note': 'Bill levies — Association keeps most since bills cover real complex expenses',
                },
                'toilet': {
                    'association_pct': 100,
                    'platform_pct':    0,
                    'note': 'Toilet revenue goes entirely to the association',
                },
            },
            'this_month_naira':    this_month / 100,
            'revenue_by_type':     by_type,
            'monthly_breakdown':   monthly,
            'recent_transactions': RevenueTransactionSerializer(
                recent_txns, many=True
            ).data,
        })


@extend_schema(tags=['Revenue'])
class AssociationRevenueTransactionsView(generics.ListAPIView):
    """
    GET /api/v1/revenue/association/transactions/
    Treasurer and President view all revenue transactions
    for their association.
    Filter by ?source_type=subscription|advert|toilet|bill
    """
    serializer_class   = RevenueTransactionSerializer
    permission_classes = [IsTreasurerOrPresident]

    def get_queryset(self):
        assoc  = self.request.user.association
        wallet = get_or_create_association_wallet(assoc)
        qs     = wallet.transactions.all()

        source_type = self.request.query_params.get('source_type')
        if source_type:
            qs = qs.filter(source_type=source_type)

        return qs


@extend_schema(tags=['Revenue'])
class AssociationRevenueDistributionsView(generics.ListAPIView):
    """
    GET /api/v1/revenue/association/distributions/
    Treasurer and President see every payment split event
    for their association.
    Filter by ?payment_type=subscription|advert|toilet|bill
    """
    serializer_class   = RevenueDistributionSerializer
    permission_classes = [IsTreasurerOrPresident]

    def get_queryset(self):
        qs = RevenueDistribution.objects.filter(
            association = self.request.user.association
        )
        payment_type = self.request.query_params.get('payment_type')
        if payment_type:
            qs = qs.filter(payment_type=payment_type)
        return qs


@extend_schema(tags=['Revenue'])
class PlatformRevenueDashboardView(APIView):
    """
    GET /api/v1/revenue/platform/dashboard/
    Super Admin only — Iprolance platform revenue dashboard.
    Shows total platform earnings across ALL associations.
    """
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        from associations.models import Association

        platform_wallet = get_or_create_platform_wallet()

        # All distributions across all associations
        all_distributions = RevenueDistribution.objects.all()

        # Platform revenue by type
        by_type = {}
        for pt in RevenueDistribution.PaymentType.choices:
            code, label = pt
            total = all_distributions.filter(
                payment_type=code
            ).aggregate(total=Sum('platform_amount'))['total'] or 0
            by_type[code] = {
                'label':       label,
                'total_naira': total / 100,
            }

        # Revenue per association
        per_association = []
        for assoc in Association.objects.filter(is_active=True):
            assoc_total = all_distributions.filter(
                association=assoc
            ).aggregate(
                total_platform=Sum('platform_amount'),
                total_collected=Sum('total_amount'),
            )
            per_association.append({
                'association':             assoc.name,
                'slug':                    assoc.slug,
                'platform_earned_naira':   (assoc_total['total_platform'] or 0) / 100,
                'total_collected_naira':   (assoc_total['total_collected'] or 0) / 100,
            })

        # This month
        this_month = all_distributions.filter(
            created_at__year  = timezone.now().year,
            created_at__month = timezone.now().month,
        ).aggregate(total=Sum('platform_amount'))['total'] or 0

        # Monthly breakdown last 6 months
        monthly = []
        from dateutil.relativedelta import relativedelta
        for i in range(5, -1, -1):
            month_date  = timezone.now() - relativedelta(months=i)
            month_total = all_distributions.filter(
                created_at__year  = month_date.year,
                created_at__month = month_date.month,
            ).aggregate(total=Sum('platform_amount'))['total'] or 0
            monthly.append({
                'month':       month_date.strftime('%Y-%m'),
                'label':       month_date.strftime('%b %Y'),
                'total_naira': month_total / 100,
            })

        return Response({
            'platform_wallet': {
                'balance_naira':         platform_wallet.balance_naira,
                'total_earned_naira':    platform_wallet.total_earned_naira,
                'total_withdrawn_naira': platform_wallet.total_withdrawn_naira,
            },
            'this_month_naira':    this_month / 100,
            'revenue_by_type':     by_type,
            'per_association':     per_association,
            'monthly_breakdown':   monthly,
            'total_associations':  Association.objects.filter(is_active=True).count(),
        })


@extend_schema(tags=['Revenue'])
class PlatformRevenueTransactionsView(generics.ListAPIView):
    """
    GET /api/v1/revenue/platform/transactions/
    Super Admin views all Iprolance platform revenue transactions.
    """
    serializer_class   = RevenueTransactionSerializer
    permission_classes = [IsSuperAdmin]

    def get_queryset(self):
        platform_wallet = get_or_create_platform_wallet()
        qs = platform_wallet.transactions.all()

        source_type = self.request.query_params.get('source_type')
        if source_type:
            qs = qs.filter(source_type=source_type)

        return qs


@extend_schema(tags=['Revenue'])
class AllDistributionsView(generics.ListAPIView):
    """
    GET /api/v1/revenue/platform/distributions/
    Super Admin views all distribution events across
    all associations.
    """
    serializer_class   = RevenueDistributionSerializer
    permission_classes = [IsSuperAdmin]

    def get_queryset(self):
        qs = RevenueDistribution.objects.all()

        assoc_slug = self.request.query_params.get('association')
        if assoc_slug:
            qs = qs.filter(association__slug=assoc_slug)

        payment_type = self.request.query_params.get('payment_type')
        if payment_type:
            qs = qs.filter(payment_type=payment_type)

        return qs


@extend_schema(tags=['Revenue'])
class RevenueWalletListView(generics.ListAPIView):
    """
    GET /api/v1/revenue/wallets/
    Super Admin sees all revenue wallets —
    association wallets and the platform wallet.
    """
    serializer_class   = RevenueWalletSummarySerializer
    permission_classes = [IsSuperAdmin]
    queryset           = RevenueWallet.objects.all()




@extend_schema(tags=['Revenue'])
class RequestWithdrawalView(APIView):
    """
    POST /api/v1/revenue/withdrawals/request/
    Treasurer requests a withdrawal from their
    association revenue wallet.
    Goes to President for approval.
    """
    permission_classes = [IsTreasurer]

    def post(self, request):
        serializer = WithdrawalRequestCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        amount = serializer.validated_data['amount']
        assoc  = request.user.association
        wallet = get_or_create_association_wallet(assoc)

        # Check sufficient revenue balance
        if wallet.balance < amount:
            return Response(
                {
                    'detail': (
                        f'Insufficient revenue balance. '
                        f'Available: ₦{wallet.balance_naira:,.2f}, '
                        f'Requested: ₦{amount/100:,.2f}.'
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        withdrawal = WithdrawalRequest.objects.create(
            revenue_wallet = wallet,
            requested_by   = request.user,
            amount         = amount,
            reason         = serializer.validated_data.get('reason', ''),
            bank_name      = serializer.validated_data.get('bank_name', ''),
            account_number = serializer.validated_data.get('account_number', ''),
            account_name   = serializer.validated_data.get('account_name', ''),
            status         = WithdrawalRequest.Status.PENDING,
        )

        # Notify President to approve
        from accounts.models import User
        from notifications.utils import send_notification as send_notif
        presidents = User.objects.filter(
            role        = 'is',
            ipos        = 'president',
            association = assoc,
            is_active   = True,
        )
        for president in presidents:
            send_notif(
                user       = president,
                category   = 'general',
                title      = f'Withdrawal Request — {withdrawal.withdrawal_ref}',
                message    = (
                    f'Treasurer {request.user.full_name} has requested a '
                    f'withdrawal of ₦{withdrawal.amount_naira:,.2f} from '
                    f'{assoc.short_name} revenue wallet. '
                    f'Please review and approve.'
                ),
                related_id = str(withdrawal.id),
            )

        return Response(
            {
                'detail':          'Withdrawal request submitted. Awaiting President approval.',
                'withdrawal_ref':  withdrawal.withdrawal_ref,
                'amount_naira':    withdrawal.amount_naira,
                'status':          withdrawal.status,
            },
            status=status.HTTP_201_CREATED
        )


@extend_schema(tags=['Revenue'])
class AssociationWithdrawalListView(generics.ListAPIView):
    """
    GET /api/v1/revenue/withdrawals/
    Treasurer and President view all withdrawal requests
    for their association.
    Filter by ?status=pending|approved|processed|rejected
    """
    serializer_class   = WithdrawalRequestSerializer
    permission_classes = [IsTreasurerOrPresident]

    def get_queryset(self):
        assoc  = self.request.user.association
        wallet = get_or_create_association_wallet(assoc)
        qs     = WithdrawalRequest.objects.filter(revenue_wallet=wallet)

        req_status = self.request.query_params.get('status')
        if req_status:
            qs = qs.filter(status=req_status)

        return qs


@extend_schema(tags=['Revenue'])
class AssociationWithdrawalDetailView(generics.RetrieveAPIView):
    """
    GET /api/v1/revenue/withdrawals/<id>/
    View a single withdrawal request.
    """
    serializer_class   = WithdrawalRequestSerializer
    permission_classes = [IsTreasurerOrPresident]

    def get_queryset(self):
        assoc  = self.request.user.association
        wallet = get_or_create_association_wallet(assoc)
        return WithdrawalRequest.objects.filter(revenue_wallet=wallet)


@extend_schema(tags=['Revenue'])
class ApproveWithdrawalView(APIView):
    """
    POST /api/v1/revenue/withdrawals/<id>/approve/
    President approves a withdrawal request.
    Triggers notification to Super Admin to process.
    """
    permission_classes = [IsPresident]

    def post(self, request, pk):
        try:
            withdrawal = WithdrawalRequest.objects.get(
                pk                        = pk,
                revenue_wallet__association = request.user.association,
            )
        except WithdrawalRequest.DoesNotExist:
            return Response(
                {'detail': 'Withdrawal request not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if withdrawal.status != WithdrawalRequest.Status.PENDING:
            return Response(
                {'detail': f'This request is already {withdrawal.status}.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        note = request.data.get('note', '')

        withdrawal.status        = WithdrawalRequest.Status.APPROVED
        withdrawal.approved_by   = request.user
        withdrawal.approved_at   = timezone.now()
        withdrawal.approval_note = note
        withdrawal.save()

        # Notify Super Admin to process
        from accounts.models import User
        from notifications.utils import send_notification as send_notif
        super_admins = User.objects.filter(role='sa', is_active=True)
        for sa in super_admins:
            send_notif(
                user       = sa,
                category   = 'general',
                title      = f'Withdrawal Approved — {withdrawal.withdrawal_ref}',
                message    = (
                    f'President {request.user.full_name} has approved withdrawal '
                    f'{withdrawal.withdrawal_ref} for ₦{withdrawal.amount_naira:,.2f} '
                    f'from {withdrawal.revenue_wallet.name}. '
                    f'Please process the bank transfer.'
                ),
                related_id = str(withdrawal.id),
            )

        # Also notify Treasurer that it was approved
        send_notif(
            user       = withdrawal.requested_by,
            category   = 'general',
            title      = f'Withdrawal Approved — {withdrawal.withdrawal_ref}',
            message    = (
                f'Your withdrawal request of ₦{withdrawal.amount_naira:,.2f} '
                f'has been approved by the President. '
                f'Funds will be transferred shortly.'
            ),
            related_id = str(withdrawal.id),
        )

        return Response({
            'detail':         'Withdrawal approved. Super Admin notified to process.',
            'withdrawal_ref': withdrawal.withdrawal_ref,
            'status':         withdrawal.status,
            'approved_at':    withdrawal.approved_at,
        })


@extend_schema(tags=['Revenue'])
class RejectWithdrawalView(APIView):
    """
    POST /api/v1/revenue/withdrawals/<id>/reject/
    President rejects a withdrawal request.
    """
    permission_classes = [IsPresident]

    def post(self, request, pk):
        try:
            withdrawal = WithdrawalRequest.objects.get(
                pk                          = pk,
                revenue_wallet__association = request.user.association,
            )
        except WithdrawalRequest.DoesNotExist:
            return Response(
                {'detail': 'Withdrawal request not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if withdrawal.status != WithdrawalRequest.Status.PENDING:
            return Response(
                {'detail': f'This request is already {withdrawal.status}.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        rejection_note = request.data.get('rejection_note', '')
        if not rejection_note:
            return Response(
                {'detail': 'A rejection note is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        withdrawal.status         = WithdrawalRequest.Status.REJECTED
        withdrawal.rejected_by    = request.user
        withdrawal.rejected_at    = timezone.now()
        withdrawal.rejection_note = rejection_note
        withdrawal.save()

        # Notify Treasurer of rejection
        from notifications.utils import send_notification as send_notif
        send_notif(
            user       = withdrawal.requested_by,
            category   = 'general',
            title      = f'Withdrawal Rejected — {withdrawal.withdrawal_ref}',
            message    = (
                f'Your withdrawal request of ₦{withdrawal.amount_naira:,.2f} '
                f'has been rejected by the President. '
                f'Reason: {rejection_note}'
            ),
            related_id = str(withdrawal.id),
        )

        return Response({
            'detail':         'Withdrawal request rejected.',
            'withdrawal_ref': withdrawal.withdrawal_ref,
            'status':         withdrawal.status,
            'rejection_note': withdrawal.rejection_note,
        })


@extend_schema(tags=['Revenue'])
class AllWithdrawalsAdminView(generics.ListAPIView):
    """
    GET /api/v1/revenue/admin/withdrawals/
    Super Admin sees ALL withdrawal requests
    across all associations.
    Filter by ?status=pending|approved|processed|rejected
    Filter by ?association=iscooa
    """
    serializer_class   = WithdrawalRequestSerializer
    permission_classes = [IsSuperAdmin]

    def get_queryset(self):
        qs = WithdrawalRequest.objects.all()

        req_status = self.request.query_params.get('status')
        if req_status:
            qs = qs.filter(status=req_status)

        assoc_slug = self.request.query_params.get('association')
        if assoc_slug:
            qs = qs.filter(
                revenue_wallet__association__slug=assoc_slug
            )

        return qs


@extend_schema(tags=['Revenue'])
class ProcessWithdrawalView(APIView):
    """
    POST /api/v1/revenue/admin/withdrawals/<id>/process/
    Super Admin processes an approved withdrawal.
    Debits the revenue wallet and records the transfer details.
    """
    permission_classes = [IsSuperAdmin]

    def post(self, request, pk):
        try:
            withdrawal = WithdrawalRequest.objects.get(pk=pk)
        except WithdrawalRequest.DoesNotExist:
            return Response(
                {'detail': 'Withdrawal request not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if withdrawal.status != WithdrawalRequest.Status.APPROVED:
            return Response(
                {
                    'detail': (
                        f'Only approved withdrawals can be processed. '
                        f'This request is {withdrawal.status}.'
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = ProcessWithdrawalSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        with db_transaction.atomic():
            # Debit the revenue wallet
            try:
                withdrawal.revenue_wallet.debit(
                    amount_kobo = withdrawal.amount,
                    description = (
                        f'Withdrawal {withdrawal.withdrawal_ref} — '
                        f'{serializer.validated_data["transfer_method"]}'
                    ),
                    ref = serializer.validated_data['transfer_ref'],
                )
            except ValueError as e:
                return Response(
                    {'detail': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Mark withdrawal as processed
            withdrawal.status          = WithdrawalRequest.Status.PROCESSED
            withdrawal.processed_by    = request.user
            withdrawal.processed_at    = timezone.now()
            withdrawal.transfer_method = serializer.validated_data['transfer_method']
            withdrawal.transfer_ref    = serializer.validated_data['transfer_ref']
            withdrawal.processing_note = serializer.validated_data.get(
                'processing_note', ''
            )
            withdrawal.save()

        # Notify Treasurer and President of completion
        from notifications.utils import send_notification as send_notif
        assoc = withdrawal.revenue_wallet.association

        # Notify Treasurer
        send_notif(
            user       = withdrawal.requested_by,
            category   = 'general',
            title      = f'Withdrawal Processed — {withdrawal.withdrawal_ref}',
            message    = (
                f'Your withdrawal of ₦{withdrawal.amount_naira:,.2f} '
                f'has been processed. '
                f'Transfer reference: {withdrawal.transfer_ref}. '
                f'Please check your bank account.'
            ),
            related_id = str(withdrawal.id),
        )

        # Notify President
        if assoc:
            from accounts.models import User
            presidents = User.objects.filter(
                role        = 'is',
                ipos        = 'president',
                association = assoc,
                is_active   = True,
            )
            for president in presidents:
                send_notif(
                    user       = president,
                    category   = 'general',
                    title      = f'Withdrawal Processed — {withdrawal.withdrawal_ref}',
                    message    = (
                        f'Withdrawal {withdrawal.withdrawal_ref} of '
                        f'₦{withdrawal.amount_naira:,.2f} has been processed. '
                        f'Transfer ref: {withdrawal.transfer_ref}.'
                    ),
                    related_id = str(withdrawal.id),
                )

        return Response({
            'detail':           'Withdrawal processed successfully.',
            'withdrawal_ref':   withdrawal.withdrawal_ref,
            'amount_naira':     withdrawal.amount_naira,
            'transfer_method':  withdrawal.transfer_method,
            'transfer_ref':     withdrawal.transfer_ref,
            'processed_at':     withdrawal.processed_at,
            'new_wallet_balance_naira': withdrawal.revenue_wallet.balance_naira,
        })