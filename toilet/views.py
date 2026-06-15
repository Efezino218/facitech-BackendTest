from django.utils import timezone
from django.db import transaction
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import ToiletPricing, ToiletSubscription
from .serializers import (
    ToiletPricingSerializer,
    ToiletSubscriptionSerializer,
    ToiletRegisterSerializer,
    ToiletRenewSerializer,
)
from .permissions import IsOperator, IsTreasurer, IsIscooaExec
from drf_spectacular.utils import extend_schema


def get_expiry_date(start_date, plan):
    """Calculate expiry date based on plan."""
    from datetime import timedelta
    from dateutil.relativedelta import relativedelta

    if plan == 'daily':
        return start_date + timedelta(days=1)
    elif plan == 'monthly':
        return start_date + relativedelta(months=1)
    elif plan == 'quarterly':
        return start_date + relativedelta(months=3)
    elif plan == 'annual':
        return start_date + relativedelta(years=1)
    return start_date


# ─── OPERATOR TOILET VIEWS ────────────────────────────────────────────────────

@extend_schema(tags=['Toilet'])
class ToiletPricingView(APIView):
    """
    GET /api/v1/toilet/pricing/
    Anyone can view current toilet pricing.
    """
    permission_classes = [IsOperator]

    def get(self, request):
        pricing = ToiletPricing.objects.filter(is_active=True).first()
        if not pricing:
            return Response(
                {'detail': 'No active toilet pricing found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = ToiletPricingSerializer(pricing)
        return Response(serializer.data)


@extend_schema(tags=['Toilet'])
class RegisterToiletView(APIView):
    """
    POST /api/v1/toilet/register/
    Operator registers a person for toilet access.
    Payment deducted from Cool MFB wallet.
    100% revenue to ISCOOA.
    """
    permission_classes = [IsOperator]

    def post(self, request):
        serializer = ToiletRegisterSerializer(
            data=request.data,
            context={'request': request}
        )
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        plan       = serializer.validated_data['plan']
        start_date = serializer.validated_data['start_date']
        shop       = serializer.validated_data['shop']

        # Get active pricing
        pricing = ToiletPricing.objects.filter(is_active=True).first()
        amount  = pricing.get_price(plan)

        # Calculate expiry
        expiry_date = get_expiry_date(start_date, plan)

        with transaction.atomic():
            # In production: debit wallet here via Cool MFB API
            subscription = serializer.save(
                registered_by = request.user,
                amount        = amount,
                expiry_date   = expiry_date,
                status        = ToiletSubscription.Status.ACTIVE,
                payment_ref   = f"TOILET-PAY-{request.user.id.hex[:8].upper()}-{timezone.now().strftime('%Y%m%d%H%M%S')}",
            )

        return Response({
            'detail':       'Toilet access registered successfully.',
            'access_ref':   subscription.access_ref,
            'full_name':    subscription.full_name,
            'plan':         subscription.plan,
            'amount_naira': subscription.amount_naira,
            'start_date':   subscription.start_date,
            'expiry_date':  subscription.expiry_date,
            'payment_ref':  subscription.payment_ref,
        }, status=status.HTTP_201_CREATED)


@extend_schema(tags=['Toilet'])
class MyToiletSubscriptionsView(generics.ListAPIView):
    """
    GET /api/v1/toilet/my-subscriptions/
    Operator sees all toilet subscriptions they registered.
    Filter by ?status=active|expired
    Filter by ?person_type=staff|customer
    """
    serializer_class   = ToiletSubscriptionSerializer
    permission_classes = [IsOperator]

    def get_queryset(self):
        qs = ToiletSubscription.objects.filter(
            registered_by=self.request.user
        )
        sub_status = self.request.query_params.get('status')
        if sub_status:
            qs = qs.filter(status=sub_status)
        person_type = self.request.query_params.get('person_type')
        if person_type:
            qs = qs.filter(person_type=person_type)
        return qs


@extend_schema(tags=['Toilet'])
class RenewToiletView(APIView):
    """
    POST /api/v1/toilet/<id>/renew/
    Operator renews a toilet subscription.
    Can renew before or after expiry.
    """
    permission_classes = [IsOperator]

    def post(self, request, pk):
        try:
            subscription = ToiletSubscription.objects.get(
                pk=pk,
                registered_by=request.user
            )
        except ToiletSubscription.DoesNotExist:
            return Response(
                {'detail': 'Subscription not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = ToiletRenewSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        plan       = serializer.validated_data['plan']
        start_date = serializer.validated_data['start_date']

        pricing     = ToiletPricing.objects.filter(is_active=True).first()
        amount      = pricing.get_price(plan)
        expiry_date = get_expiry_date(start_date, plan)

        with transaction.atomic():
            subscription.plan        = plan
            subscription.amount      = amount
            subscription.start_date  = start_date
            subscription.expiry_date = expiry_date
            subscription.status      = ToiletSubscription.Status.ACTIVE
            subscription.payment_ref = f"TOILET-RENEW-{request.user.id.hex[:8].upper()}-{timezone.now().strftime('%Y%m%d%H%M%S')}"
            subscription.save()

        return Response({
            'detail':       'Toilet subscription renewed successfully.',
            'access_ref':   subscription.access_ref,
            'full_name':    subscription.full_name,
            'plan':         subscription.plan,
            'amount_naira': subscription.amount_naira,
            'start_date':   subscription.start_date,
            'expiry_date':  subscription.expiry_date,
        })


# ─── ISCOOA TREASURER TOILET VIEWS ───────────────────────────────────────────

@extend_schema(tags=['Toilet'])
class AllToiletSubscriptionsView(generics.ListAPIView):
    """
    GET /api/v1/toilet/all/
    Treasurer sees all toilet subscriptions.
    Filter by ?status=active|expired
    Filter by ?person_type=staff|customer
    Filter by ?plan=daily|monthly|quarterly|annual
    """
    serializer_class   = ToiletSubscriptionSerializer
    permission_classes = [IsTreasurer]

    def get_queryset(self):
        qs = ToiletSubscription.objects.all()
        sub_status = self.request.query_params.get('status')
        if sub_status:
            qs = qs.filter(status=sub_status)
        person_type = self.request.query_params.get('person_type')
        if person_type:
            qs = qs.filter(person_type=person_type)
        plan = self.request.query_params.get('plan')
        if plan:
            qs = qs.filter(plan=plan)
        return qs


@extend_schema(tags=['Toilet'])
class ToiletRevenueSummaryView(APIView):
    """
    GET /api/v1/toilet/revenue-summary/
    Treasurer sees total toilet revenue.
    100% goes to ISCOOA.
    """
    permission_classes = [IsTreasurer]

    def get(self, request):
        from django.db.models import Sum, Count

        all_subs = ToiletSubscription.objects.all()

        totals = all_subs.aggregate(
            total_revenue = Sum('amount'),
            total_count   = Count('id'),
        )

        active_count   = all_subs.filter(status='active').count()
        expired_count  = all_subs.filter(status='expired').count()
        staff_count    = all_subs.filter(person_type='staff').count()
        customer_count = all_subs.filter(person_type='customer').count()

        # Revenue by plan
        by_plan = {}
        for plan in ['daily', 'monthly', 'quarterly', 'annual']:
            plan_total = all_subs.filter(plan=plan).aggregate(
                total=Sum('amount')
            )['total'] or 0
            by_plan[plan] = plan_total / 100

        return Response({
            'total_revenue_naira':  (totals['total_revenue'] or 0) / 100,
            'total_subscribers':    totals['total_count'],
            'active_count':         active_count,
            'expired_count':        expired_count,
            'staff_count':          staff_count,
            'customer_count':       customer_count,
            'revenue_by_plan':      by_plan,
            'note':                 '100% of toilet revenue goes to ISCOOA. No Iprolance cut.',
        })


@extend_schema(tags=['Toilet'])
class UpdateToiletPricingView(APIView):
    """
    PUT /api/v1/toilet/pricing/update/
    Treasurer updates toilet pricing.
    """
    permission_classes = [IsTreasurer]

    def put(self, request):
        pricing = ToiletPricing.objects.filter(is_active=True).first()
        if not pricing:
            # Create first pricing record
            pricing = ToiletPricing.objects.create(updated_by=request.user)

        serializer = ToiletPricingSerializer(
            pricing,
            data=request.data,
            partial=True
        )
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            return Response({
                'detail':  'Toilet pricing updated successfully.',
                'pricing': serializer.data,
            })
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )