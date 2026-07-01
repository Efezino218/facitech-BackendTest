from django.utils import timezone
from django.db import transaction
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response

from shops.models import Shop
from .models import Subscription, SubscriptionPayment
from .serializers import (
    SubscriptionSerializer, SubscriptionListSerializer,
    CycleSelectSerializer,
)
from .permissions import IsOperator, IsTreasurer, IsIscooaExec
from drf_spectacular.utils import extend_schema


# ─── OPERATOR VIEWS ───────────────────────────────────────────────────────────

@extend_schema(tags=['Subscriptions'])
class MySubscriptionView(APIView):
    """
    GET /api/v1/subscriptions/my-subscription/
    Operator views their subscription detail.
    Free trial starts from KYC approval date.
    Billing starts one month after approval.
    Shop count is always synced to current active shops.
    """
    permission_classes = [IsOperator]

    def get(self, request):
        from shops.models import Shop

        # Get subscription rate from association config
        default_rate = 100000
        try:
            default_rate = request.user.association.config.subscription_rate
        except Exception:
            pass

        # Current active shop count — always live count
        current_shop_count = Shop.objects.filter(
            operator  = request.user,
            is_active = True
        ).count() or 1

        subscription, created = Subscription.objects.get_or_create(
            operator = request.user,
            defaults = {
                'status':        Subscription.Status.KYC,
                'current_month': 1,
                'shop_count':    current_shop_count,
                'rate_per_shop': default_rate,
            }
        )

        # Always sync shop count to current active shops
        # This ensures if operator added shops after
        # subscription was created the count is always fresh
        if subscription.shop_count != current_shop_count:
            subscription.shop_count = current_shop_count
            subscription.save()

        serializer = SubscriptionSerializer(subscription)
        data = serializer.data

        # Add extra context for the frontend subscription page
        data['billing_explanation'] = (
            f'Your subscription covers all {current_shop_count} active shop(s). '
            f'Monthly fee: ₦{(default_rate * current_shop_count / 100):,.2f}. '
            f'All shops added before your billing date are included in the same payment.'
        )

        if subscription.status == Subscription.Status.KYC:
            data['trial_message'] = (
                'Month 1 is free. Your billing starts on '
                f'{subscription.renewal_date or "the date your KYC was approved + 30 days"}.'
            )

        return Response(data)


@extend_schema(tags=['Subscriptions'])
class PaySubscriptionView(APIView):
    """
    POST /api/v1/subscriptions/pay/
    Operator selects a cycle and pays their subscription
    via Cool MFB wallet.
    Month 1 is always free — no payment needed.
    """
    permission_classes = [IsOperator]

    def post(self, request):
        serializer = CycleSelectSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        cycle = serializer.validated_data['cycle']

        try:
            subscription = request.user.subscription
        except Subscription.DoesNotExist:
            return Response(
                {'detail': 'Subscription record not found. Please visit your subscription page first.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Month 1 is free — no payment needed
        if subscription.current_month == 1:
            return Response(
                {
                    'detail': 'Month 1 is free during your KYC period. No payment required.',
                    'current_month': subscription.current_month,
                    'status': subscription.status,
                }
            )

        # Update cycle on subscription
        subscription.cycle = cycle
        subscription.save()

        # Calculate amounts
        # Sync shop count to current active shops at payment time
        from shops.models import Shop
        current_shop_count = Shop.objects.filter(
            operator  = request.user,
            is_active = True
        ).count() or 1

        if subscription.shop_count != current_shop_count:
            subscription.shop_count = current_shop_count
            subscription.save()

        # Calculate amounts based on current shop count
        # This ensures all shops added before payment date are included
        amount = subscription.cycle_total()

        # Get revenue split from association config
        assoc_share    = 20
        platform_share = 80
        try:
            config         = request.user.association.config
            assoc_share    = config.association_share
            platform_share = config.platform_share
        except Exception:
            pass

        iscooa_cut    = int(amount * (assoc_share / 100))
        iprolance_cut = int(amount * (platform_share / 100))

        # Determine billing period string
        period = timezone.now().strftime('%Y-%m')

        with transaction.atomic():
            # In production: call Cool MFB wallet API here
            # For now we simulate a successful payment
            payment = SubscriptionPayment.objects.create(
                subscription  = subscription,
                operator      = request.user,
                period        = period,
                cycle         = cycle,
                shop_count    = subscription.shop_count,
                amount        = amount,
                iscooa_cut    = iscooa_cut,
                iprolance_cut = iprolance_cut,
                status        = SubscriptionPayment.Status.PAID,
                payment_ref   = f"COOLMFB-SUB-{request.user.member_number}-{timezone.now().strftime('%Y%m%d%H%M%S')}",
                paid_at       = timezone.now(),
            )

            # Advance subscription month
            subscription.current_month += 1
            subscription.status         = Subscription.Status.ACTIVE
            subscription.renewal_date   = timezone.now().date().replace(
                month=timezone.now().month + 1
                if timezone.now().month < 12
                else 1
            )
            subscription.save()

        return Response({
            'detail':               'Subscription payment successful.',
            'period':               period,
            'cycle':                cycle,
            'shop_count':           subscription.shop_count,
            'amount_naira':         payment.amount_naira,
            'iscooa_cut_naira':     payment.iscooa_cut_naira,
            'iprolance_cut_naira':  payment.iprolance_cut_naira,
            'payment_ref':          payment.payment_ref,
            'current_month':        subscription.current_month,
            'billing_note': (
                f'Payment covers {subscription.shop_count} shop(s). '
                f'All shops active at payment time are included.'
            ),
        })


# ─── ISCOOA EXECUTIVE VIEWS ───────────────────────────────────────────────────

@extend_schema(tags=['Subscriptions'])
class AllSubscriptionsView(generics.ListAPIView):
    """
    GET /api/v1/subscriptions/all/
    Treasurer sees subscriptions for their OWN association only.
    Filter by ?status=active|kyc|overdue|suspended
    """
    serializer_class   = SubscriptionListSerializer
    permission_classes = [IsTreasurer]

    def get_queryset(self):
        qs = Subscription.objects.filter(
            operator__association = self.request.user.association
        )
        sub_status = self.request.query_params.get('status')
        if sub_status:
            qs = qs.filter(status=sub_status)
        return qs


@extend_schema(tags=['Subscriptions'])
class SubscriptionDetailAdminView(generics.RetrieveAPIView):
    """
    GET /api/v1/subscriptions/all/<id>/
    Treasurer views full subscription detail —
    scoped to their own association.
    """
    serializer_class   = SubscriptionSerializer
    permission_classes = [IsTreasurer]

    def get_queryset(self):
        return Subscription.objects.filter(
            operator__association = self.request.user.association
        )


@extend_schema(tags=['Subscriptions'])
class CommissionSummaryView(APIView):
    """
    GET /api/v1/subscriptions/commission-summary/
    Treasurer sees total subscription commissions.
    Breaks down ISCOOA 20% and Iprolance 80%.
    """
    permission_classes = [IsTreasurer]

    def get(self, request):
        from django.db.models import Sum

        payments = SubscriptionPayment.objects.filter(
            status = SubscriptionPayment.Status.PAID,
            operator__association  = request.user.association,
        )

        # Optional filter by period e.g. ?period=2026-05
        period = request.query_params.get('period')
        if period:
            payments = payments.filter(period=period)

        totals = payments.aggregate(
            total_amount    = Sum('amount'),
            total_iscooa    = Sum('iscooa_cut'),
            total_iprolance = Sum('iprolance_cut'),
        )

        return Response({
            'total_collected_naira':    (totals['total_amount'] or 0) / 100,
            'iscooa_commission_naira':  (totals['total_iscooa'] or 0) / 100,
            'iprolance_share_naira':    (totals['total_iprolance'] or 0) / 100,
            'payment_count':            payments.count(),
            'period_filter':            period or 'all time',
        })