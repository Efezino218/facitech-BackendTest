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
from rest_framework.permissions import IsAuthenticated



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


def get_active_pricing_for_user(user):
    """
    Get active toilet pricing for the user's association.
    Returns None if no pricing found.
    """
    return ToiletPricing.objects.filter(
        association = user.association,
        is_active   = True
    ).first()


# ─── OPERATOR TOILET VIEWS ────────────────────────────────────────────────────

class ToiletPricingView(APIView):
    """
    GET /api/v1/toilet/pricing/
    Any authenticated user (operator or association executive)
    can view pricing for their own association.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Only operators and ISCOOA execs have an association-scoped
        # toilet pricing context — everyone else gets a clear 403
        if request.user.role not in ['op', 'is']:
            return Response(
                {'detail': 'This endpoint is for operators and association executives only.'},
                status=status.HTTP_403_FORBIDDEN
            )

        pricing = get_active_pricing_for_user(request.user)
        if not pricing:
            assoc_name = 'Your Association'
            try:
                assoc_name = request.user.association.name
            except Exception:
                pass
            return Response(
                {
                    'detail': (
                        f'No active toilet pricing found. '
                        f'Please contact {assoc_name} Treasurer.'
                    )
                },
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = ToiletPricingSerializer(pricing)
        return Response(serializer.data)


class RegisterToiletView(APIView):
    """
    POST /api/v1/toilet/register/
    Operator registers a person for toilet access.
    Checks wallet balance, debits the amount, then creates
    the subscription ONLY if payment succeeds.
    100% revenue to the association.
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

        # Get active pricing for this association
        pricing = get_active_pricing_for_user(request.user)
        amount  = pricing.get_price(plan)
        expiry_date = get_expiry_date(start_date, plan)

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

        # Step 1 — Check balance BEFORE creating anything
        if wallet.balance < amount:
            return Response(
                {
                    'detail': (
                        f'Insufficient wallet balance. '
                        f'Available: ₦{wallet.balance_naira:,.2f}, '
                        f'Required: ₦{amount / 100:,.2f}. '
                        f'Please top up your wallet.'
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Step 2 — Debit wallet and create subscription atomically
        # If either fails, both roll back — no partial state.
        with transaction.atomic():
            payment_ref = (
                f"TOILET-PAY-{request.user.id.hex[:8].upper()}-"
                f"{timezone.now().strftime('%Y%m%d%H%M%S')}"
            )

            # Debit happens first — raises ValueError if balance changed
            # between the check above and now (race condition safety)
            try:
                wallet.debit(
                    amount_kobo = amount,
                    description = (
                        f'Toilet access — {serializer.validated_data["full_name"]} '
                        f'({plan})'
                    ),
                    method = 'wallet',
                    ref    = payment_ref,
                )
            except ValueError as e:
                return Response(
                    {'detail': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Step 3 — Only create the subscription AFTER payment succeeds
            subscription = serializer.save(
                registered_by = request.user,
                association   = request.user.association,
                amount        = amount,
                expiry_date   = expiry_date,
                status        = ToiletSubscription.Status.ACTIVE,
                payment_ref   = payment_ref,
            )

        return Response({
            'detail':                   'Toilet access registered and payment confirmed.',
            'access_ref':               subscription.access_ref,
            'full_name':                subscription.full_name,
            'plan':                     subscription.plan,
            'amount_naira':             subscription.amount_naira,
            'start_date':               subscription.start_date,
            'expiry_date':              subscription.expiry_date,
            'payment_ref':              subscription.payment_ref,
            'new_wallet_balance_naira': wallet.balance_naira,
        }, status=status.HTTP_201_CREATED)
    

class MyToiletSubscriptionsView(generics.ListAPIView):
    """
    GET /api/v1/toilet/my-subscriptions/
    Operator sees toilet subscriptions they registered.
    Scoped to their own association.
    Filter by ?status=active|expired
    Filter by ?person_type=staff|customer
    """
    serializer_class   = ToiletSubscriptionSerializer
    permission_classes = [IsOperator]

    def get_queryset(self):
        qs = ToiletSubscription.objects.filter(
            registered_by = self.request.user,
            association   = self.request.user.association,
        )
        sub_status = self.request.query_params.get('status')
        if sub_status:
            qs = qs.filter(status=sub_status)
        person_type = self.request.query_params.get('person_type')
        if person_type:
            qs = qs.filter(person_type=person_type)
        return qs


class RenewToiletView(APIView):
    """
    POST /api/v1/toilet/<id>/renew/
    Operator renews a toilet subscription.
    Checks wallet balance, debits the renewal amount,
    then updates the subscription ONLY if payment succeeds.
    """
    permission_classes = [IsOperator]

    def post(self, request, pk):
        try:
            subscription = ToiletSubscription.objects.get(
                pk            = pk,
                registered_by = request.user,
                association   = request.user.association,
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

        pricing = get_active_pricing_for_user(request.user)
        if not pricing:
            assoc_name = 'Your Association'
            try:
                assoc_name = request.user.association.name
            except Exception:
                pass
            return Response(
                {
                    'detail': (
                        f'No active toilet pricing found. '
                        f'Please contact {assoc_name} Treasurer.'
                    )
                },
                status=status.HTTP_404_NOT_FOUND
            )

        amount      = pricing.get_price(plan)
        expiry_date = get_expiry_date(start_date, plan)

        # Get or create wallet
        from wallet.models import Wallet
        wallet, _ = Wallet.objects.get_or_create(
            operator=request.user,
            defaults={
                'balance': 0,
                'coolmfb_account_number': f"COOL{request.user.id.hex[:10].upper()}",
                'coolmfb_account_name':   request.user.full_name or request.user.email,
            }
        )

        # Check balance before touching anything
        if wallet.balance < amount:
            return Response(
                {
                    'detail': (
                        f'Insufficient wallet balance. '
                        f'Available: ₦{wallet.balance_naira:,.2f}, '
                        f'Required: ₦{amount / 100:,.2f}. '
                        f'Please top up your wallet.'
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            payment_ref = (
                f"TOILET-RENEW-{request.user.id.hex[:8].upper()}-"
                f"{timezone.now().strftime('%Y%m%d%H%M%S')}"
            )

            try:
                wallet.debit(
                    amount_kobo = amount,
                    description = f'Toilet renewal — {subscription.full_name} ({plan})',
                    method      = 'wallet',
                    ref         = payment_ref,
                )
            except ValueError as e:
                return Response(
                    {'detail': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Only update the subscription AFTER payment succeeds
            subscription.plan        = plan
            subscription.amount      = amount
            subscription.start_date  = start_date
            subscription.expiry_date = expiry_date
            subscription.status      = ToiletSubscription.Status.ACTIVE
            subscription.payment_ref = payment_ref
            subscription.save()

        return Response({
            'detail':                   'Toilet subscription renewed and payment confirmed.',
            'access_ref':               subscription.access_ref,
            'full_name':                subscription.full_name,
            'plan':                     subscription.plan,
            'amount_naira':             subscription.amount_naira,
            'start_date':               subscription.start_date,
            'expiry_date':              subscription.expiry_date,
            'new_wallet_balance_naira': wallet.balance_naira,
        })
    
    

# ─── ISCOOA TREASURER TOILET VIEWS ───────────────────────────────────────────

class AllToiletSubscriptionsView(generics.ListAPIView):
    """
    GET /api/v1/toilet/all/
    Treasurer sees only their association's toilet subscriptions.
    Filter by ?status=active|expired
    Filter by ?person_type=staff|customer
    Filter by ?plan=daily|monthly|quarterly|annual
    """
    serializer_class   = ToiletSubscriptionSerializer
    permission_classes = [IsTreasurer]

    def get_queryset(self):
        # Treasurer only sees their own association
        qs = ToiletSubscription.objects.filter(
            association=self.request.user.association
        )
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


class ToiletRevenueSummaryView(APIView):
    """
    GET /api/v1/toilet/revenue-summary/
    Treasurer sees total toilet revenue for their association.
    100% goes to the association.
    """
    permission_classes = [IsTreasurer]

    def get(self, request):
        from django.db.models import Sum, Count

        # Scoped to this treasurer's association
        all_subs = ToiletSubscription.objects.filter(
            association=request.user.association
        )

        totals = all_subs.aggregate(
            total_revenue = Sum('amount'),
            total_count   = Count('id'),
        )

        active_count   = all_subs.filter(status='active').count()
        expired_count  = all_subs.filter(status='expired').count()
        staff_count    = all_subs.filter(person_type='staff').count()
        customer_count = all_subs.filter(person_type='customer').count()

        by_plan = {}
        for plan in ['daily', 'monthly', 'quarterly', 'annual']:
            plan_total = all_subs.filter(plan=plan).aggregate(
                total=Sum('amount')
            )['total'] or 0
            by_plan[plan] = plan_total / 100

        # Dynamic association name
        assoc_name = 'Association'
        try:
            assoc_name = request.user.association.name
        except Exception:
            pass

        return Response({
            'association':          assoc_name,
            'total_revenue_naira':  (totals['total_revenue'] or 0) / 100,
            'total_subscribers':    totals['total_count'],
            'active_count':         active_count,
            'expired_count':        expired_count,
            'staff_count':          staff_count,
            'customer_count':       customer_count,
            'revenue_by_plan':      by_plan,
            'note':                 f'100% of toilet revenue goes to {assoc_name}. No platform cut.',
        })


class UpdateToiletPricingView(APIView):
    """
    PUT /api/v1/toilet/pricing/update/
    Treasurer updates toilet pricing for their association.
    Cannot update another association's pricing.
    """
    permission_classes = [IsTreasurer]

    def put(self, request):
        # Get or create pricing for THIS association only
        pricing, created = ToiletPricing.objects.get_or_create(
            association = request.user.association,
            is_active   = True,
            defaults    = {
                'updated_by': request.user,
            }
        )

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