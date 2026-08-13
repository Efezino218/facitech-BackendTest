from django.utils import timezone
from django.db import transaction
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from audit.models import log_action
from notifications.utils import send_notification, send_bulk_notification
from accounts.models import User

from .models import Bill, ExternalPayment, generate_invoice_id
from .serializers import (
    BillSerializer, BillCreateSerializer,
    ExternalPaymentSerializer, ExternalPaymentCreateSerializer,
)
from .permissions import (
    IsOperator, IsIscooaExec,
    IsTreasurer, IsTreasurerOrSecretary,
)
from drf_spectacular.utils import extend_schema


# ─── OPERATOR BILL VIEWS ──────────────────────────────────────────────────────

@extend_schema(tags=['Bills'])
class MyBillsView(generics.ListAPIView):
    """
    GET /api/v1/bills/my-bills/
    Operator sees all their own bills.
    Filter by status using ?status=unpaid|paid|verified
    Filter by period using ?period=2026-05
    """
    serializer_class   = BillSerializer
    permission_classes = [IsOperator]

    def get_queryset(self):
        qs = Bill.objects.filter(operator=self.request.user)
        bill_status = self.request.query_params.get('status')
        if bill_status:
            qs = qs.filter(status=bill_status)
        period = self.request.query_params.get('period')
        if period:
            qs = qs.filter(billing_period=period)
        return qs


@extend_schema(tags=['Bills'])
class MyBillDetailView(generics.RetrieveAPIView):
    """
    GET /api/v1/bills/my-bills/<id>/
    Operator views a single bill detail.
    """
    serializer_class   = BillSerializer
    permission_classes = [IsOperator]

    def get_queryset(self):
        return Bill.objects.filter(operator=self.request.user)


class PayBillView(APIView):
    """
    POST /api/v1/bills/my-bills/<id>/pay/
    Operator pays a bill via Cool MFB Wallet.
    Debits the wallet immediately and marks bill as paid.
    Fails with 400 if wallet balance is insufficient.
    In production this will call the Cool MFB API.
    """
    permission_classes = [IsOperator]

    def post(self, request, pk):
        try:
            bill = Bill.objects.get(pk=pk, operator=request.user)
        except Bill.DoesNotExist:
            return Response(
                {'detail': 'Bill not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if bill.status != Bill.Status.UNPAID:
            return Response(
                {'detail': f'Bill is already {bill.status}.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get or create the operator's wallet
        from wallet.models import Wallet
        wallet, _ = Wallet.objects.get_or_create(
            operator=request.user,
            defaults={
                'balance': 0,
                'coolmfb_account_number': f"COOL{request.user.id.hex[:10].upper()}",
                'coolmfb_account_name':   request.user.full_name or request.user.email,
            }
        )

        # Check sufficient balance BEFORE making any changes
        if wallet.balance < bill.total:
            return Response(
                {
                    'detail': (
                        f'Insufficient wallet balance. '
                        f'Available: ₦{wallet.balance_naira:,.2f}, '
                        f'Required: ₦{bill.total_naira:,.2f}. '
                        f'Please top up your wallet.'
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            paid_ref = f"COOLMFB-{bill.invoice_id}-{timezone.now().strftime('%Y%m%d%H%M%S')}"

            # Debit the wallet — this also creates the transaction record
            wallet.debit(
                amount_kobo = bill.total,
                description = f'Payment for bill {bill.invoice_id} ({bill.billing_period})',
                method      = 'wallet',
                ref         = paid_ref,
            )

            # Mark bill as paid
            bill.status   = Bill.Status.PAID
            bill.paid_at  = timezone.now()
            bill.paid_ref = paid_ref
            bill.save()


            # Notify treasurer that a bill has been paid
            treasurer_users = User.objects.filter(
                role        = 'is',
                ipos        = 'treasurer',
                association = request.user.association,
                is_active   = True,
            )
            send_bulk_notification(
                users      = treasurer_users,
                category   = 'bills',
                title      = f'Bill Paid — {bill.invoice_id}',
                message    = (
                    f'Operator {request.user.full_name or request.user.email} '
                    f'has paid bill {bill.invoice_id} '
                    f'(₦{bill.total_naira:,.2f}). Awaiting your verification.'
                ),
                related_id = str(bill.id),
            )

        return Response({
            'detail':            'Payment successful. Awaiting ISCOOA verification.',
            'invoice_id':        bill.invoice_id,
            'paid_ref':          bill.paid_ref,
            'status':            bill.status,
            'amount_debited_naira': bill.total_naira,
            'new_wallet_balance_naira': wallet.balance_naira,
        })

# ─── EXTERNAL PAYMENT VIEWS (Operator) ───────────────────────────────────────

@extend_schema(tags=['Bills'])
class MyExternalPaymentsView(generics.ListAPIView):
    """
    GET /api/v1/bills/external-payments/
    Operator sees all their external payment registrations.
    """
    serializer_class   = ExternalPaymentSerializer
    permission_classes = [IsOperator]

    def get_queryset(self):
        return ExternalPayment.objects.filter(operator=self.request.user)


@extend_schema(tags=['Bills'])
class RegisterExternalPaymentView(generics.CreateAPIView):
    """
    POST /api/v1/bills/external-payments/register/
    Operator registers an external payment.

    Two modes:
    1. WITH bill link — amount locked to exact bill total.
       billing_period and shop auto-filled from bill.
       No partial payments or overpayments accepted.

    2. WITHOUT bill link — free-form amount for payments
       not linked to a specific ISCOOA invoice
       e.g. EKEDC electricity paid directly.
    """
    serializer_class   = ExternalPaymentCreateSerializer
    permission_classes = [IsOperator]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data    = request.data,
            context = self.get_serializer_context()
        )
        serializer.is_valid(raise_exception=True)
        external_payment = serializer.save(operator=request.user)

        # Build response with clear indication of what was auto-filled
        response_data = {
            'detail':          'External payment registered successfully. Awaiting Treasurer verification.',
            'id':              str(external_payment.id),
            'status':          external_payment.status,
            'amount_naira':    external_payment.amount / 100,
            'billing_period':  external_payment.billing_period,
            'channel':         external_payment.channel,
            'reference':       external_payment.reference,
        }

        if external_payment.bill:
            response_data['bill_linked']    = True
            response_data['invoice_id']     = external_payment.bill.invoice_id
            response_data['shop_number']    = external_payment.shop.shop_number
            response_data['note'] = (
                f'Amount locked to exact bill total of '
                f'₦{external_payment.amount/100:,.2f}. '
                f'Bill will be automatically marked as verified once Treasurer approves.'
            )
        else:
            response_data['bill_linked'] = False
            response_data['note'] = (
                'No bill linked. Treasurer will verify this payment manually.'
            )

        return Response(response_data, status=status.HTTP_201_CREATED)



@extend_schema(tags=['Bills'])
class MyUnpaidBillsView(generics.ListAPIView):
    """
    GET /api/v1/bills/my-unpaid-bills/
    Operator sees their unpaid bills that can be linked
    to an external payment.
    Only shows bills with no pending external payment.
    Used to populate the bill selector on the external
    payment form.
    """
    serializer_class   = BillSerializer
    permission_classes = [IsOperator]

    def get_queryset(self):
        # Get unpaid bills with no pending external payment
        from django.db.models import Q
        return Bill.objects.filter(
            operator = self.request.user,
            status   = 'unpaid',
        ).exclude(
            external_payments__status='pending'
        ).order_by('-created_at')


# ─── ISCOOA EXECUTIVE BILL VIEWS ──────────────────────────────────────────────

@extend_schema(tags=['Bills'])
class AllBillsView(generics.ListAPIView):
    """
    GET /api/v1/bills/all/
    Association Executive sees bills for their OWN association only.
    Filter by ?status=unpaid|paid|verified
    Filter by ?period=2026-05
    Filter by ?shop=B-11
    """
    serializer_class   = BillSerializer
    permission_classes = [IsIscooaExec]

    def get_queryset(self):
        qs = Bill.objects.filter(
            operator__association = self.request.user.association
        )
        bill_status = self.request.query_params.get('status')
        if bill_status:
            qs = qs.filter(status=bill_status)
        period = self.request.query_params.get('period')
        if period:
            qs = qs.filter(billing_period=period)
        shop = self.request.query_params.get('shop')
        if shop:
            qs = qs.filter(shop__shop_number__icontains=shop)
        return qs

@extend_schema(tags=['Bills'])
class RaiseBillView(generics.CreateAPIView):
    """
    POST /api/v1/bills/raise/
    Treasurer raises a new HFP bill for a shop.
    """
    serializer_class   = BillCreateSerializer
    permission_classes = [IsTreasurer]


    def create(self, request, *args, **kwargs):
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            billing_period = serializer.validated_data['billing_period']
            shop           = serializer.validated_data['shop']
            invoice_id     = generate_invoice_id(billing_period)
            bill = serializer.save(
                invoice_id = invoice_id,
                operator   = shop.operator,
                raised_by  = request.user,
            )

            # Notify operator that a new bill has been raised
            send_notification(
                user       = bill.operator,
                category   = 'bills',
                title      = f'New Bill — {bill.invoice_id}',
                message    = (
                    f'A new bill ({bill.invoice_id}) has been raised for shop '
                    f'{bill.shop.shop_number} for period {bill.billing_period}. '
                    f'Amount due: ₦{bill.total_naira:,.2f}.'
                ),
                related_id = str(bill.id),
            )

            log_action(
                user        = request.user,
                action      = 'create',
                table_name  = 'bills',
                record_id   = str(bill.id),
                record_ref  = bill.invoice_id,
                description = f'Bill raised for shop {bill.shop.shop_number} period {bill.billing_period}. Total: ₦{bill.total/100}',
                request     = request,
            )



            return Response(
                {
                    'detail':      'Bill raised successfully.',
                    'invoice_id':  bill.invoice_id,
                    'total_naira': bill.total / 100,
                },
                status=status.HTTP_201_CREATED
            )


@extend_schema(tags=['Bills'])
class VerifyBillView(APIView):
    """
    POST /api/v1/bills/<id>/verify/
    Treasurer or Secretary verifies a paid bill.
    Can only verify bills belonging to their own association.
    """
    permission_classes = [IsTreasurerOrSecretary]

    def post(self, request, pk):
        try:
            bill = Bill.objects.get(
                pk = pk,
                operator__association = request.user.association,
            )
        except Bill.DoesNotExist:
            return Response(
                {'detail': 'Bill not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Only paid bills can be verified
        if bill.status != Bill.Status.PAID:
            return Response(
                {'detail': 'Only paid bills can be verified.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Don't verify twice
        if bill.status == Bill.Status.VERIFIED:
            return Response(
                {'detail': 'Bill is already verified.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            bill.status      = Bill.Status.VERIFIED
            bill.verified_by = request.user
            bill.verified_at = timezone.now()
            bill.save()

            # ── Distribute bill revenue ────────────────────────────────
            # ── Distribute bill revenue ────────────────────────────────
            # Bills are ISCOOA levy collections — 100% to association
            # Iprolance does not take a cut on bill payments
            try:
                from revenue.utils import distribute_revenue
                from revenue.models import RevenueDistribution
                distribute_revenue(
                    association           = bill.operator.association,
                    operator              = bill.operator,
                    total_amount_kobo     = bill.total,
                    payment_type          = RevenueDistribution.PaymentType.BILL,
                    source_ref            = bill.invoice_id,
                    association_share_pct = 100,
                    platform_share_pct    = 0,
                    note                  = (
                        f'HFP Bill — {bill.invoice_id} '
                        f'Period: {bill.billing_period} '
                        f'Shop: {bill.shop.shop_number}'
                    ),
                )
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(
                    f'Revenue distribution failed for bill {bill.invoice_id}: {e}'
                )


        # Notify operator their bill has been verified
        send_notification(
            user=bill.operator,
            category='bills',
            title=f'Bill Verified — {bill.invoice_id}',
            message=(
                f'Your payment for bill {bill.invoice_id} '
                f'has been verified. Your receipt is now available.'
            ),
            related_id=str(bill.id),
        )

        serializer = BillSerializer(bill)
        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema(tags=['Bills'])
class AllExternalPaymentsView(generics.ListAPIView):
    """
    GET /api/v1/bills/external-payments/all/
    Association Executive sees external payments for
    their OWN association only.
    Filter by ?status=pending|verified|rejected
    """
    serializer_class   = ExternalPaymentSerializer
    permission_classes = [IsIscooaExec]

    def get_queryset(self):
        qs = ExternalPayment.objects.filter(
            operator__association = self.request.user.association
        )
        ep_status = self.request.query_params.get('status')
        if ep_status:
            qs = qs.filter(status=ep_status)
        return qs


@extend_schema(tags=['Bills'])
class VerifyExternalPaymentView(APIView):
    """
    POST /api/v1/bills/external-payments/<id>/verify/
    ISCOOA Executive verifies an external payment.
    """
    permission_classes = [IsTreasurerOrSecretary]

    def post(self, request, pk):
        try:
            ep = ExternalPayment.objects.get(
                pk                    = pk,
                operator__association = request.user.association,
            )
        except ExternalPayment.DoesNotExist:
            return Response(
                {'detail': 'External payment not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if ep.status != 'pending':
            return Response(
                {'detail': f'This payment is already {ep.status}.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        verified_amount = request.data.get('verified_amount', ep.amount)
        note            = request.data.get('note', '')

        with transaction.atomic():
            ep.status          = ExternalPayment.Status.VERIFIED
            ep.verified_by     = request.user
            ep.verified_at     = timezone.now()
            ep.verified_amount = verified_amount
            ep.save()

            # ── Auto-mark linked bill as verified ──────────────────────
            bill_auto_verified = False
            if ep.bill and ep.bill.status in ['unpaid', 'paid']:
                ep.bill.status      = Bill.Status.VERIFIED
                ep.bill.verified_by = request.user
                ep.bill.verified_at = timezone.now()
                # Use a special ref to indicate external payment
                ep.bill.paid_ref    = f"EXT-{ep.reference or str(ep.id)[:8].upper()}"
                if not ep.bill.paid_at:
                    ep.bill.paid_at = timezone.now()
                ep.bill.save()
                bill_auto_verified = True

            # ── Distribute external payment revenue ────────────────────
            # 100% to association — money was received directly
            try:
                from revenue.utils import distribute_revenue
                from revenue.models import RevenueDistribution
                distribute_revenue(
                    association           = ep.operator.association,
                    operator              = ep.operator,
                    total_amount_kobo     = ep.verified_amount,
                    payment_type          = RevenueDistribution.PaymentType.EXTERNAL_PAYMENT,
                    source_ref            = str(ep.id),
                    association_share_pct = 100,
                    platform_share_pct    = 0,
                    note                  = (
                        f'External payment verified — '
                        f'{ep.get_category_display()} '
                        f'Period: {ep.billing_period} '
                        f'Shop: {ep.shop.shop_number}. '
                        f'Money received directly by association.'
                        + (f' Linked bill: {ep.bill.invoice_id}' if ep.bill else '')
                    ),
                )
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(
                    f'Revenue distribution failed for external payment {ep.id}: {e}'
                )

            # Notify operator
            bill_message = ''
            if bill_auto_verified:
                bill_message = (
                    f' Your bill {ep.bill.invoice_id} '
                    f'has been automatically marked as verified.'
                )

            from notifications.utils import send_notification
            send_notification(
                user       = ep.operator,
                category   = 'bills',
                title      = 'External Payment Verified',
                message    = (
                    f'Your external payment of ₦{ep.amount_naira:,.2f} '
                    f'for period {ep.billing_period} has been verified.'
                    + bill_message
                ),
                related_id = str(ep.id),
            )

        return Response({
            'detail':               'External payment verified.',
            'verified_amount_naira': ep.verified_amount / 100,
            'bill_auto_verified':    bill_auto_verified,
            'bill_invoice_id':       ep.bill.invoice_id if ep.bill else None,
            'bill_status':           ep.bill.status if ep.bill else None,
        })


@extend_schema(tags=['Bills'])
class RejectExternalPaymentView(APIView):
    """
    POST /api/v1/bills/external-payments/<id>/reject/
    ISCOOA Executive rejects an external payment.
    """
    permission_classes = [IsTreasurerOrSecretary]

    def post(self, request, pk):
        try:
            ep = ExternalPayment.objects.get(
                pk = pk,
                operator__association = request.user.association,
            )
        except ExternalPayment.DoesNotExist:
            return Response(
                {'detail': 'External payment not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        rejection_note = request.data.get('rejection_note', '')
        if not rejection_note:
            return Response(
                {'detail': 'A rejection note is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        ep.status         = ExternalPayment.Status.REJECTED
        ep.rejection_note = rejection_note
        ep.verified_by    = request.user
        ep.verified_at    = timezone.now()
        ep.save()

        # Notify operator their external payment was rejected
        send_notification(
                user       = ep.operator,
                category   = 'bills',
                title      = 'External Payment Rejected',
                message    = (
                    f'Your external payment of ₦{ep.amount_naira:,.2f} '
                    f'for period {ep.billing_period} has been rejected. '
                    f'Reason: {rejection_note}'
                ),
                related_id = str(ep.id),
            )

        return Response({
            'detail': 'External payment rejected.',
            'status': ep.status,
        })