from django.utils import timezone
from django.db import transaction
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import Wallet, WalletTransaction
from .serializers import WalletSerializer, TopUpSerializer, WalletTransactionSerializer
from .permissions import IsOperator, IsIscooaExec, IsSuperAdmin
from drf_spectacular.utils import extend_schema


# ─── OPERATOR WALLET VIEWS ────────────────────────────────────────────────────

@extend_schema(tags=['Wallet'])
class MyWalletView(APIView):
    """
    GET /api/v1/wallet/my-wallet/
    Operator views their wallet balance and
    recent transaction history.
    Auto-creates wallet if not yet created.
    """
    permission_classes = [IsOperator]

    def get(self, request):
        wallet, created = Wallet.objects.get_or_create(
            operator=request.user,
            defaults={
                'balance': 0,
                'coolmfb_account_number': f"COOL{request.user.id.hex[:10].upper()}",
                'coolmfb_account_name':   request.user.full_name or request.user.email,
            }
        )
        serializer = WalletSerializer(wallet)
        return Response(serializer.data)


@extend_schema(tags=['Wallet'])
class TopUpWalletView(APIView):
    """
    POST /api/v1/wallet/top-up/
    Operator tops up their Cool MFB wallet.
    In production this calls Paystack or Cool MFB API.
    For now we simulate a successful top-up.
    """
    permission_classes = [IsOperator]

    def post(self, request):
        serializer = TopUpSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        amount = serializer.validated_data['amount']
        method = serializer.validated_data['method']

        wallet, _ = Wallet.objects.get_or_create(
            operator=request.user,
            defaults={
                'balance': 0,
                'coolmfb_account_number': f"COOL{request.user.id.hex[:10].upper()}",
                'coolmfb_account_name':   request.user.full_name,
            }
        )

        with transaction.atomic():
            # In production: verify payment with Paystack or Cool MFB first
            # then credit wallet only after confirmation
            txn = wallet.credit(
                amount_kobo = amount,
                description = f'Wallet top-up via {method}',
                method      = method,
                ref         = f"TOPUP-{request.user.id.hex[:8].upper()}-{timezone.now().strftime('%Y%m%d%H%M%S')}",
            )

        return Response({
            'detail':           'Wallet top-up successful.',
            'amount_naira':     txn.amount_naira,
            'method':           method,
            'reference':        txn.reference,
            'new_balance_naira': wallet.balance_naira,
        })


@extend_schema(tags=['Wallet'])
class WalletTransactionListView(generics.ListAPIView):
    """
    GET /api/v1/wallet/transactions/
    Operator views their full transaction history.
    Filter by ?type=credit|debit
    """
    serializer_class   = WalletTransactionSerializer
    permission_classes = [IsOperator]

    def get_queryset(self):
        qs = WalletTransaction.objects.filter(operator=self.request.user)
        txn_type = self.request.query_params.get('type')
        if txn_type:
            qs = qs.filter(type=txn_type)
        return qs


@extend_schema(tags=['Wallet'])
class WalletSummaryView(APIView):
    """
    GET /api/v1/wallet/summary/
    Operator sees a quick summary of their wallet.
    Shows balance, total paid this month, outstanding bills.
    """
    permission_classes = [IsOperator]

    def get(self, request):
        from django.db.models import Sum
        from bills.models import Bill

        try:
            wallet = request.user.wallet
        except Wallet.DoesNotExist:
            return Response({
                'balance_naira':            0,
                'bills_outstanding_naira':  0,
                'fees_paid_this_month_naira': 0,
            })

        # Outstanding bills total
        outstanding = Bill.objects.filter(
            operator=request.user,
            status='unpaid'
        ).aggregate(total=Sum('total'))['total'] or 0

        # Fees paid this month (debits this month)
        this_month = timezone.now().replace(day=1)
        paid_this_month = WalletTransaction.objects.filter(
            operator    = request.user,
            type        = WalletTransaction.Type.DEBIT,
            created_at__gte = this_month,
        ).aggregate(total=Sum('amount'))['total'] or 0

        return Response({
            'balance_naira':                wallet.balance_naira,
            'bills_outstanding_naira':      outstanding / 100,
            'fees_paid_this_month_naira':   paid_this_month / 100,
            'coolmfb_account_number':       wallet.coolmfb_account_number,
            'coolmfb_account_name':         wallet.coolmfb_account_name,
        })


# ─── ISCOOA EXECUTIVE WALLET VIEWS ───────────────────────────────────────────

@extend_schema(tags=['Wallet'])
class AllWalletsView(generics.ListAPIView):
    """
    GET /api/v1/wallet/all/
    ISCOOA Executive sees all operator wallets.
    Read only — oversight only.
    """
    serializer_class   = WalletSerializer
    permission_classes = [IsIscooaExec]

    def get_queryset(self):
        return Wallet.objects.all().order_by('-balance')


@extend_schema(tags=['Wallet'])
class OperatorWalletDetailView(generics.RetrieveAPIView):
    """
    GET /api/v1/wallet/all/<id>/
    ISCOOA Executive views a specific operator wallet
    with full transaction history.
    """
    serializer_class   = WalletSerializer
    permission_classes = [IsIscooaExec]
    queryset           = Wallet.objects.all()