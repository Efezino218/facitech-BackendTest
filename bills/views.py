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
    Operator registers an external payment with evidence.
    operator is always set from request.user — never accepted from the request body.
    """
    serializer_class   = ExternalPaymentCreateSerializer
    permission_classes = [IsOperator]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data=request.data,
            context=self.get_serializer_context()
        )
        serializer.is_valid(raise_exception=True)
        external_payment = serializer.save(operator=request.user)

        
        # Notify treasurer of new external payment
        treasurer_users = User.objects.filter(
            role        = 'is',
            ipos        = 'treasurer',
            association = request.user.association,
            is_active   = True,
        )
        send_bulk_notification(
            users      = treasurer_users,
            category   = 'bills',
            title      = 'External Payment Registered',
            message    = (
                f'Operator {request.user.full_name or request.user.email} '
                f'has registered an external payment of '
                f'₦{external_payment.amount_naira:,.2f} '
                f'for period {external_payment.billing_period}. '
                f'Awaiting your verification.'
            ),
            related_id = str(external_payment.id),
        )

        return Response(
            self.get_serializer(external_payment).data,
            status=status.HTTP_201_CREATED
        )



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
            # Bill revenue split: 80% association, 20% platform
            # (Association keeps most since bills cover real expenses)
            try:
                from revenue.utils import distribute_revenue
                from revenue.models import RevenueDistribution

                # Get bill-specific split from association config
                bill_assoc_share    = 80
                bill_platform_share = 20
                try:
                    config              = bill.operator.association.config
                    bill_assoc_share    = config.bill_association_share
                    bill_platform_share = config.bill_platform_share
                except Exception:
                    pass

                distribute_revenue(
                    association           = bill.operator.association,
                    operator              = bill.operator,
                    total_amount_kobo     = bill.total,
                    payment_type          = RevenueDistribution.PaymentType.BILL,
                    source_ref            = bill.invoice_id,
                    association_share_pct = bill_assoc_share,
                    platform_share_pct    = bill_platform_share,
                    note                  = (
                        f'HFP Bill verified — {bill.invoice_id} '
                        f'Period: {bill.billing_period} '
                        f'Shop: {bill.shop.shop_number}'
                    ),
                )
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(
                    f'Revenue distribution failed for bill {bill.invoice_id}: {e}'
                )

            # Notify operator
            send_notification(
                user       = bill.operator,
                category   = 'bills',
                title      = f'Bill Verified — {bill.invoice_id}',
                message    = (
                    f'Your payment for bill {bill.invoice_id} '
                    f'has been verified. Your receipt is now available.'
                ),
                related_id = str(bill.id),
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
                pk = pk,
                operator__association = request.user.association,
            )
        except ExternalPayment.DoesNotExist:
            return Response(
                {'detail': 'External payment not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if ep.status != ExternalPayment.Status.PENDING:
            return Response(
                {'detail': 'This payment has already been reviewed.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Executive may confirm a different verified amount
        verified_amount = request.data.get('verified_amount', ep.amount)

        with transaction.atomic():
            ep.status      = ExternalPayment.Status.VERIFIED
            ep.verified_by = request.user
            ep.verified_at = timezone.now()
            ep.verified_amount = verified_amount
            ep.save()

            # ── Distribute external payment revenue ────────────────────
            # External payments cover bills paid outside the platform
            # Same split as bills: 80% association, 20% platform
            try:
                from revenue.utils import distribute_revenue
                from revenue.models import RevenueDistribution

                bill_assoc_share    = 80
                bill_platform_share = 20
                try:
                    config              = ep.operator.association.config
                    bill_assoc_share    = config.bill_association_share
                    bill_platform_share = config.bill_platform_share
                except Exception:
                    pass

                # Use verified_amount not the submitted amount
                distribute_revenue(
                    association           = ep.operator.association,
                    operator              = ep.operator,
                    total_amount_kobo     = ep.verified_amount,
                    payment_type          = RevenueDistribution.PaymentType.EXTERNAL_PAYMENT,
                    source_ref            = str(ep.id),
                    association_share_pct = bill_assoc_share,
                    platform_share_pct    = bill_platform_share,
                    note                  = (
                        f'External payment verified — '
                        f'{ep.get_category_display()} '
                        f'Period: {ep.billing_period} '
                        f'Shop: {ep.shop.shop_number}'
                    ),
                )
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(
                    f'Revenue distribution failed for external payment {ep.id}: {e}'
                )

            # Notify operator
            send_notification(
                user       = ep.operator,
                category   = 'bills',
                title      = 'External Payment Verified',
                message    = (
                    f'Your external payment of ₦{ep.amount_naira:,.2f} '
                    f'for period {ep.billing_period} has been verified.'
                ),
                related_id = str(ep.id),
            )

        # Notify operator their external payment was verified
        send_notification(
                user       = ep.operator,
                category   = 'bills',
                title      = 'External Payment Verified',
                message    = (
                    f'Your external payment of ₦{ep.amount_naira:,.2f} '
                    f'for period {ep.billing_period} has been verified.'
                ),
                related_id = str(ep.id),
            )

        return Response({
            'detail': 'External payment verified.',
            'status': ep.status,
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