import json
import logging
from django.utils import timezone
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Wallet, WalletTransaction, PaystackTransaction
from .serializers import WalletSerializer, TopUpSerializer, WalletTransactionSerializer
from .permissions import IsOperator, IsIscooaExec, IsSuperAdmin
from .paystack import initialize_transaction, verify_transaction, verify_webhook_signature

logger = logging.getLogger(__name__)


def get_or_create_wallet(user):
    """Helper to get or create wallet for a user."""
    wallet, _ = Wallet.objects.get_or_create(
        operator=user,
        defaults={
            'balance': 0,
            'coolmfb_account_number': f"COOL{user.id.hex[:10].upper()}",
            'coolmfb_account_name':   user.full_name or user.email,
        }
    )
    return wallet


# ─── OPERATOR WALLET VIEWS ────────────────────────────────────────────────────

class MyWalletView(APIView):
    """
    GET /api/v1/wallet/my-wallet/
    Operator views their wallet balance and
    recent transaction history.
    """
    permission_classes = [IsOperator]

    def get(self, request):
        wallet = get_or_create_wallet(request.user)
        serializer = WalletSerializer(wallet)
        return Response(serializer.data)


class InitializeTopUpView(APIView):
    """
    POST /api/v1/wallet/top-up/initialize/
    Operator initializes a Paystack top-up.
    Returns authorization_url to redirect user to Paystack payment page.
    After payment Paystack calls our webhook to credit the wallet.

    Body: { "amount": 1000000 }  ← amount in kobo e.g. 1000000 = ₦10,000
    """
    permission_classes = [IsOperator]

    def post(self, request):
        amount_kobo = request.data.get('amount')

        if not amount_kobo:
            return Response(
                {'detail': 'amount is required (in kobo). e.g. 1000000 for ₦10,000'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            amount_kobo = int(amount_kobo)
        except (ValueError, TypeError):
            return Response(
                {'detail': 'amount must be a valid integer in kobo.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Minimum top-up: ₦100 = 10000 kobo
        if amount_kobo < 10000:
            return Response(
                {'detail': 'Minimum top-up amount is ₦100 (10000 kobo).'},
                status=status.HTTP_400_BAD_REQUEST
            )

        wallet = get_or_create_wallet(request.user)

        # Build metadata to attach to the Paystack transaction
        # This comes back in the webhook so we know which wallet to credit
        metadata = {
            'wallet_id':    str(wallet.id),
            'operator_id':  str(request.user.id),
            'operator_email': request.user.email,
            'platform':     'iscooa_facitech',
        }

        # Initialize with Paystack
        result = initialize_transaction(
            email       = request.user.email,
            amount_kobo = amount_kobo,
            metadata    = metadata,
        )

        if not result['success']:
            return Response(
                {'detail': f"Paystack error: {result['error']}"},
                status=status.HTTP_502_BAD_GATEWAY
            )

        # Save pending transaction record
        # This prevents double-crediting if webhook fires twice
        PaystackTransaction.objects.create(
            operator  = request.user,
            wallet    = wallet,
            reference = result['reference'],
            amount    = amount_kobo,
            status    = PaystackTransaction.Status.PENDING,
        )

        return Response({
            'detail':            'Paystack transaction initialized.',
            'authorization_url': result['authorization_url'],
            'access_code':       result['access_code'],
            'reference':         result['reference'],
            'amount_naira':      amount_kobo / 100,
            'instructions': (
                'Redirect the user to authorization_url to complete payment. '
                'Wallet will be credited automatically after payment confirmation.'
            ),
        })


class TopUpWalletView(APIView):
    """
    POST /api/v1/wallet/top-up/
    SIMULATION MODE — for testing without real Paystack.
    Comment this out in production and use InitializeTopUpView instead.
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

        wallet = get_or_create_wallet(request.user)

        with transaction.atomic():
            # ── SIMULATION MODE ────────────────────────────────────────
            # In production replace this block with real Cool MFB API call
            # and remove the simulation comment
            txn = wallet.credit(
                amount_kobo = amount,
                description = f'Wallet top-up via {method} [SIMULATION]',
                method      = method,
                ref         = f"SIM-TOPUP-{request.user.id.hex[:8].upper()}-{timezone.now().strftime('%Y%m%d%H%M%S')}",
            )
            # ── END SIMULATION MODE ────────────────────────────────────

        return Response({
            'detail':            'Wallet top-up successful. [SIMULATION MODE]',
            'amount_naira':      txn.amount_naira,
            'method':            method,
            'reference':         txn.reference,
            'new_balance_naira': wallet.balance_naira,
        })


class PaystackCallbackView(APIView):
    """
    GET /api/v1/wallet/paystack/callback/
    Paystack redirects user here after payment on their page.
    We verify the transaction and show a result.
    The webhook is the authoritative source — this is just for UX.
    """
    permission_classes = []  # No auth — Paystack redirects here

    def get(self, request):
        reference = request.query_params.get('reference')
        if not reference:
            return Response(
                {'detail': 'No reference provided.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if already credited via webhook
        try:
            paystack_txn = PaystackTransaction.objects.get(reference=reference)
            if paystack_txn.wallet_credited:
                return Response({
                    'detail':      'Payment confirmed. Wallet has been credited.',
                    'reference':   reference,
                    'amount_naira': paystack_txn.amount_naira,
                    'status':      'success',
                })
        except PaystackTransaction.DoesNotExist:
            pass

        # Verify with Paystack directly as fallback
        result = verify_transaction(reference)
        if not result['success']:
            return Response(
                {'detail': f"Could not verify payment: {result['error']}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if result['status'] == 'success':
            # Credit wallet if not already done
            _credit_wallet_for_reference(reference, result)
            return Response({
                'detail':      'Payment confirmed. Wallet has been credited.',
                'reference':   reference,
                'amount_naira': result['amount'] / 100,
                'status':      'success',
            })

        return Response({
            'detail':  f"Payment status: {result['status']}. Wallet not credited.",
            'status':  result['status'],
        })


@method_decorator(csrf_exempt, name='dispatch')
class PaystackWebhookView(APIView):
    """
    POST /api/v1/wallet/paystack/webhook/
    Paystack sends payment events here.
    We verify the signature then credit the wallet.
    This is the authoritative payment confirmation.
    CSRF exempt — Paystack cannot send a CSRF token.
    """
    permission_classes = []
    authentication_classes = []

    def post(self, request):
        # Step 1 — Verify the signature to confirm this is from Paystack
        signature = request.headers.get('X-Paystack-Signature', '')
        if not signature:
            logger.warning('Paystack webhook received with no signature header')
            return Response(
                {'detail': 'Missing signature.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        payload_bytes = request.body
        if not verify_webhook_signature(payload_bytes, signature):
            logger.warning('Paystack webhook signature verification failed')
            return Response(
                {'detail': 'Invalid signature.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Step 2 — Parse the event
        try:
            payload = json.loads(payload_bytes)
        except json.JSONDecodeError:
            return Response(
                {'detail': 'Invalid JSON payload.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        event = payload.get('event')
        data  = payload.get('data', {})

        logger.info(f'Paystack webhook received: {event}')

        # Step 3 — Handle charge.success event
        if event == 'charge.success':
            reference = data.get('reference')
            amount    = data.get('amount')

            if not reference:
                return Response(
                    {'detail': 'No reference in webhook data.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            _credit_wallet_for_reference(reference, {
                'status':    'success',
                'amount':    amount,
                'email':     data.get('customer', {}).get('email', ''),
                'reference': reference,
                'metadata':  data.get('metadata', {}),
            })

        # Always return 200 to Paystack — even if we skip processing
        # Paystack retries if it gets a non-200 response
        return Response({'detail': 'Webhook received.'})


def _credit_wallet_for_reference(reference, paystack_data):
    """
    Internal helper — credits the wallet for a successful Paystack payment.
    Uses select_for_update to prevent race conditions.
    Idempotent — safe to call multiple times for the same reference.
    """
    with transaction.atomic():
        try:
            paystack_txn = PaystackTransaction.objects.select_for_update().get(
                reference = reference
            )
        except PaystackTransaction.DoesNotExist:
            logger.error(f'PaystackTransaction not found for reference: {reference}')
            return

        # Idempotency check — do not credit twice
        if paystack_txn.wallet_credited:
            logger.info(f'Wallet already credited for reference: {reference}')
            return

        if paystack_data.get('status') != 'success':
            paystack_txn.status       = PaystackTransaction.Status.FAILED
            paystack_txn.paystack_data = paystack_data
            paystack_txn.save()
            logger.info(f'Payment not successful for reference: {reference}')
            return

        # Credit the wallet
        wallet = paystack_txn.wallet
        wallet.credit(
            amount_kobo = paystack_txn.amount,
            description = f'Wallet top-up via Paystack',
            method      = 'paystack',
            ref         = reference,
        )

        # Mark as credited — prevents double-crediting
        paystack_txn.status          = PaystackTransaction.Status.SUCCESS
        paystack_txn.wallet_credited = True
        paystack_txn.paystack_data   = paystack_data
        paystack_txn.save()

        logger.info(
            f'Wallet credited: {wallet.operator.email} '
            f'₦{paystack_txn.amount_naira} ref={reference}'
        )


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


class WalletSummaryView(APIView):
    """
    GET /api/v1/wallet/summary/
    Operator sees a quick summary of their wallet.
    """
    permission_classes = [IsOperator]

    def get(self, request):
        from django.db.models import Sum
        from bills.models import Bill

        try:
            wallet = request.user.wallet
        except Wallet.DoesNotExist:
            return Response({
                'balance_naira':              0,
                'bills_outstanding_naira':    0,
                'fees_paid_this_month_naira': 0,
            })

        outstanding = Bill.objects.filter(
            operator = request.user,
            status   = 'unpaid'
        ).aggregate(total=Sum('total'))['total'] or 0

        this_month = timezone.now().replace(day=1)
        paid_this_month = WalletTransaction.objects.filter(
            operator        = request.user,
            type            = WalletTransaction.Type.DEBIT,
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

class AllWalletsView(generics.ListAPIView):
    """
    GET /api/v1/wallet/all/
    Association Executive sees wallets for their own association only.
    """
    serializer_class   = WalletSerializer
    permission_classes = [IsIscooaExec]

    def get_queryset(self):
        return Wallet.objects.filter(
            operator__association = self.request.user.association
        ).order_by('-balance')


class OperatorWalletDetailView(generics.RetrieveAPIView):
    """
    GET /api/v1/wallet/all/<id>/
    Association Executive views a specific operator wallet.
    """
    serializer_class   = WalletSerializer
    permission_classes = [IsIscooaExec]

    def get_queryset(self):
        return Wallet.objects.filter(
            operator__association = self.request.user.association
        )