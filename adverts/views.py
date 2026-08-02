from django.utils import timezone
from django.db import transaction
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema
from datetime import timedelta

from .models import Advert
from .serializers import AdvertSerializer, AdvertListSerializer, AdvertCreateSerializer
from .permissions import (
    IsOperator, IsSecretaryGeneral, IsIscooaExec,
    IsSecretaryOrPresident,
)


# def get_advert_fee(category, duration_days, association):
#     """
#     Calculate advert fee based on category and duration.
#     Configurable per association in the future.
#     Current flat rates:
#         Promo / New Stock / Services / General: ₦1,000 for 7 days
#         Vacancy: ₦2,000 for 30 days
#     """
#     base_rates = {
#         'promo':     100000,  # ₦1,000
#         'new_stock': 100000,
#         'services':  100000,
#         'general':   100000,
#         'vacancy':   200000,  # ₦2,000
#     }
#     base  = base_rates.get(category, 100000)
#     # Simple: extra duration doubles the fee
#     extra = (duration_days // 7) - 1
#     if extra > 0:
#         base = int(base * (1 + extra * 0.5))
#     return base


# ─── OPERATOR VIEWS ───────────────────────────────────────────────────────────

@extend_schema(tags=['Adverts'])
class SubmitAdvertView(APIView):
    """
    POST /api/v1/adverts/submit/
    Operator submits a new advert for review.
    Fee is calculated on submission.
    Wallet is NOT debited yet — only debited on approval.
    """
    permission_classes = [IsOperator]

    def post(self, request):
        serializer = AdvertCreateSerializer(
            data=request.data,
            context={'request': request}
        )
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        category     = serializer.validated_data.get('category', 'general')
        duration     = serializer.validated_data.get('duration_days', 7)
        # Fee is auto-calculated in Advert.save() from CATEGORY_FEES
        # No manual calculation needed here
        fee = Advert.CATEGORY_FEES.get(category, 100000)

        with transaction.atomic():
            advert = serializer.save(
                operator    = request.user,
                association = request.user.association,
                fee         = fee,
                status      = Advert.Status.PENDING,
                is_live     = False,
            )

        # Notify Secretary General
        from accounts.models import User
        from notifications.utils import send_bulk_notification
        sec_users = User.objects.filter(
            role        = 'is',
            ipos        = 'secretary_general',
            association = request.user.association,
            is_active   = True,
        )
        send_bulk_notification(
            users      = sec_users,
            category   = 'adverts',
            title      = 'New Advert Submission',
            message    = (
                f'Operator {request.user.full_name or request.user.email} '
                f'submitted a {advert.get_category_display()} advert: '
                f'"{advert.headline}". '
                f'Fee: ₦{advert.fee_naira:,.2f}. Awaiting your review.'
            ),
            related_id = str(advert.id),
        )

        return Response({
            'detail':   'Advert submitted successfully. Awaiting Secretary General review.',
            'id':       str(advert.id),
            'headline': advert.headline,
            'category': advert.category,
            'fee_naira': advert.fee_naira,
            'status':   advert.status,
            'note': (
                f'Your wallet will be debited ₦{advert.fee_naira:,.2f} '
                f'only if your advert is approved.'
            ),
        }, status=status.HTTP_201_CREATED)


@extend_schema(tags=['Adverts'])
class MyAdvertsView(generics.ListAPIView):
    """
    GET /api/v1/adverts/my-adverts/
    Operator views their own advert submissions.
    Filter by ?status=pending|approved|rejected|expired
    """
    serializer_class   = AdvertListSerializer
    permission_classes = [IsOperator]

    def get_queryset(self):
        qs = Advert.objects.filter(
            operator    = self.request.user,
            association = self.request.user.association,
        )
        advert_status = self.request.query_params.get('status')
        if advert_status:
            qs = qs.filter(status=advert_status)
        return qs


@extend_schema(tags=['Adverts'])
class MyAdvertDetailView(generics.RetrieveAPIView):
    """
    GET /api/v1/adverts/my-adverts/<id>/
    Operator views detail of their own advert.
    """
    serializer_class   = AdvertSerializer
    permission_classes = [IsOperator]

    def get_queryset(self):
        return Advert.objects.filter(
            operator    = self.request.user,
            association = self.request.user.association,
        )


# ─── MARKETPLACE VIEWS ────────────────────────────────────────────────────────

@extend_schema(tags=['Adverts'])
class MarketplaceView(generics.ListAPIView):
    """
    GET /api/v1/adverts/marketplace/
    ALL live approved adverts visible to ALL authenticated
    users across ALL associations on the platform.
    Operators pay to advertise — their adverts deserve
    maximum visibility across the entire platform.
    Filter by ?category=promo|new_stock|vacancy|services|general
    Filter by ?association=iscooa (optional — filter by slug)
    """
    serializer_class   = AdvertListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        now = timezone.now()

        # Auto-expire across all associations before returning
        Advert.objects.filter(
            status      = Advert.Status.APPROVED,
            is_live     = True,
            expires_at__lt = now,
        ).update(status=Advert.Status.EXPIRED, is_live=False)

        # Platform-wide — no association filter
        qs = Advert.objects.filter(
            status     = Advert.Status.APPROVED,
            is_live    = True,
            expires_at__gt = now,    # Only truly live and not expired
        )

        category = self.request.query_params.get('category')
        if category:
            qs = qs.filter(category=category)

        # Optional filter by association slug
        assoc_slug = self.request.query_params.get('association')
        if assoc_slug:
            qs = qs.filter(association__slug=assoc_slug)

        return qs.order_by('-approved_at')
    

@extend_schema(tags=['Adverts'])
class DashboardCarouselView(APIView):
    """
    GET /api/v1/adverts/carousel/
    Latest 5 live adverts across the ENTIRE platform.
    Visible to all authenticated users including
    operators from any association, executives and Super Admin.
    Only shows truly live adverts — expired are excluded.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        now = timezone.now()

        # Auto-expire before querying
        Advert.objects.filter(
            status         = Advert.Status.APPROVED,
            is_live        = True,
            expires_at__lt = now,
        ).update(status=Advert.Status.EXPIRED, is_live=False)

        # Platform-wide — all associations
        adverts = Advert.objects.filter(
            status         = Advert.Status.APPROVED,
            is_live        = True,
            expires_at__gt = now,    # Strictly not expired
        ).select_related(
            'operator', 'shop', 'association'
        ).order_by('-approved_at')[:5]

        data = []
        for advert in adverts:
            # Build contact info — use advert contact if provided
            # otherwise fall back to operator/shop defaults
            contact = {
                'phone':     advert.contact_phone or advert.operator.phone or '',
                'email':     advert.contact_email or advert.operator.email or '',
                'whatsapp':  advert.contact_whatsapp or '',
                'instagram': advert.contact_instagram or '',
                'facebook':  advert.contact_facebook or '',
            }

            data.append({
                'id':               str(advert.id),
                'headline':         advert.headline,
                'description':      advert.description[:150],
                'category':         advert.category,
                'category_display': advert.get_category_display(),
                'image_url':        advert.image_url,
                'association_name': advert.association.name if advert.association else '',
                'association_slug': advert.association.slug if advert.association else '',
                'operator_name':    advert.operator.full_name or advert.operator.email,
                'shop_number':      advert.shop.shop_number if advert.shop else '',
                'contact':          contact,
                'expires_at':       advert.expires_at,
                'days_remaining':   (advert.expires_at - now).days if advert.expires_at else None,
            })

        return Response({
            'count':   len(data),
            'adverts': data,
        })


# ─── SECRETARY GENERAL VIEWS ──────────────────────────────────────────────────

@extend_schema(tags=['Adverts'])
class AdvertQueueView(generics.ListAPIView):
    """
    GET /api/v1/adverts/queue/
    Secretary General and President view the advert queue.
    Secretary can approve/reject.
    President can view only.
    Filter by ?status=pending|approved|rejected|expired
    """
    serializer_class   = AdvertListSerializer
    permission_classes = [IsIscooaExec]

    def get_queryset(self):
        qs = Advert.objects.filter(
            association = self.request.user.association
        )
        advert_status = self.request.query_params.get('status')
        if advert_status:
            qs = qs.filter(status=advert_status)
        return qs.order_by('-created_at')


@extend_schema(tags=['Adverts'])
class AdvertDetailAdminView(generics.RetrieveAPIView):
    """
    GET /api/v1/adverts/queue/<id>/
    Secretary General and President view full advert detail.
    """
    serializer_class   = AdvertSerializer
    permission_classes = [IsIscooaExec]

    def get_queryset(self):
        return Advert.objects.filter(
            association = self.request.user.association
        )


@extend_schema(tags=['Adverts'])
class ApproveAdvertView(APIView):
    """
    POST /api/v1/adverts/<id>/approve/
    Secretary General approves an advert.
    Flow:
        1. Check operator wallet balance
        2. Debit wallet
        3. Calculate revenue split
        4. Credit association and platform revenue wallets
        5. Mark advert as approved and live
        6. Set expiry date
    """
    permission_classes = [IsSecretaryGeneral]

    def post(self, request, pk):
        try:
            advert = Advert.objects.get(
                pk          = pk,
                association = request.user.association,
            )
        except Advert.DoesNotExist:
            return Response(
                {'detail': 'Advert not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if advert.status != Advert.Status.PENDING:
            return Response(
                {'detail': f'Advert is already {advert.status}.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ── Check operator wallet balance ─────────────────────────────
        from wallet.models import Wallet
        wallet, _ = Wallet.objects.get_or_create(
            operator = advert.operator,
            defaults = {
                'balance': 0,
                'coolmfb_account_number': f"COOL{advert.operator.id.hex[:10].upper()}",
                'coolmfb_account_name':   advert.operator.full_name or advert.operator.email,
            }
        )

        if wallet.balance < advert.fee:
            # Notify operator their balance is insufficient
            from notifications.utils import send_notification
            send_notification(
                user       = advert.operator,
                category   = 'adverts',
                title      = 'Advert Approved But Payment Failed',
                message    = (
                    f'Your advert "{advert.headline}" was approved by the Secretary '
                    f'but could not go live because your wallet balance is insufficient. '
                    f'Required: ₦{advert.fee_naira:,.2f}. '
                    f'Available: ₦{wallet.balance_naira:,.2f}. '
                    f'Please top up your wallet and contact the Secretary to resubmit.'
                ),
                related_id = str(advert.id),
            )
            return Response(
                {
                    'detail': (
                        f'Cannot approve — operator wallet balance insufficient. '
                        f'Required: ₦{advert.fee_naira:,.2f}, '
                        f'Available: ₦{wallet.balance_naira:,.2f}. '
                        f'Operator has been notified to top up.'
                    ),
                    'wallet_insufficient': True,
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # ── Calculate revenue split ───────────────────────────────────
        assoc_share    = 20
        platform_share = 80
        try:
            config         = advert.association.config
            assoc_share    = config.association_share
            platform_share = config.platform_share
        except Exception:
            pass

        iscooa_cut    = int(advert.fee * (assoc_share / 100))
        iprolance_cut = int(advert.fee * (platform_share / 100))

        now        = timezone.now()
        expires_at = now + timedelta(days=advert.duration_days)

        with transaction.atomic():
            # ── 1. Debit operator wallet ──────────────────────────────
            payment_ref = f"ADV-{str(advert.id)[:8].upper()}-{now.strftime('%Y%m%d%H%M%S')}"
            try:
                wallet.debit(
                    amount_kobo = advert.fee,
                    description = f'Advert fee — "{advert.headline}" ({advert.get_category_display()})',
                    method      = 'wallet',
                    ref         = payment_ref,
                )
            except ValueError as e:
                return Response(
                    {'detail': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # ── 2. Distribute revenue ─────────────────────────────────
            try:
                from revenue.utils import distribute_revenue
                from revenue.models import RevenueDistribution
                distribute_revenue(
                    association       = advert.association,
                    operator          = advert.operator,
                    total_amount_kobo = advert.fee,
                    payment_type      = RevenueDistribution.PaymentType.ADVERT,
                    source_ref        = payment_ref,
                    note              = f'Advert fee — "{advert.headline}"',
                )
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(
                    f'Revenue distribution failed for advert {advert.id}: {e}'
                )

            # ── 3. Approve advert and make it live ────────────────────
            advert.status         = Advert.Status.APPROVED
            advert.is_live        = True
            advert.reviewed_by    = request.user
            advert.reviewed_at    = now
            advert.approved_at    = now
            advert.live_from      = now       # ← your field name
            advert.expires_at     = expires_at
            advert.iscooa_cut     = iscooa_cut
            advert.iprolance_cut  = iprolance_cut
            advert.save()

        # ── Notify operator ───────────────────────────────────────────
        from notifications.utils import send_notification
        send_notification(
            user       = advert.operator,
            category   = 'adverts',
            title      = 'Advert Approved and Live',
            message    = (
                f'Your advert "{advert.headline}" has been approved. '
                f'₦{advert.fee_naira:,.2f} has been deducted from your wallet. '
                f'Your advert is now live and will expire on '
                f'{expires_at.strftime("%d %b %Y")}.'
            ),
            related_id = str(advert.id),
        )

        return Response({
            'detail':       'Advert approved, wallet debited and advert is now live.',
            'id':           str(advert.id),
            'headline':     advert.headline,
            'status':       advert.status,
            'is_live':      advert.is_live,
            'fee_charged_naira': advert.fee_naira,
            'approved_at':  advert.approved_at,
            'expires_at':   advert.expires_at,
            'operator_new_wallet_balance_naira': wallet.balance_naira,
        })


@extend_schema(tags=['Adverts'])
class RejectAdvertView(APIView):
    """
    POST /api/v1/adverts/<id>/reject/
    Secretary General rejects an advert.
    No wallet debit — operator is not charged for rejected adverts.
    """
    permission_classes = [IsSecretaryGeneral]

    def post(self, request, pk):
        try:
            advert = Advert.objects.get(
                pk          = pk,
                association = request.user.association,
            )
        except Advert.DoesNotExist:
            return Response(
                {'detail': 'Advert not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if advert.status != Advert.Status.PENDING:
            return Response(
                {'detail': f'Advert is already {advert.status}.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        reject_reason = request.data.get('reason', '')
        if not reject_reason:
            return Response(
                {'detail': 'A rejection reason is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        advert.status       = Advert.Status.REJECTED
        advert.is_live      = False
        advert.reviewed_by  = request.user
        advert.reviewed_at  = timezone.now()
        advert.reject_reason = reject_reason   # ← your field name
        advert.save()

        # Notify operator — no charge
        from notifications.utils import send_notification
        send_notification(
            user       = advert.operator,
            category   = 'adverts',
            title      = 'Advert Rejected',
            message    = (
                f'Your advert "{advert.headline}" has been rejected. '
                f'Reason: {reject_reason}. '
                f'No charge has been made to your wallet. '
                f'You may resubmit after making the required changes.'
            ),
            related_id = str(advert.id),
        )

        return Response({
            'detail':         'Advert rejected. No charge to operator wallet.',
            'headline':       advert.headline,
            'status':         advert.status,
            'rejection_reason': advert.rejection_reason,
        })


@extend_schema(tags=['Adverts'])
class TakeOfflineView(APIView):
    """
    POST /api/v1/adverts/<id>/take-offline/
    Secretary General takes a live advert offline.
    No refund — operator was already charged on approval.
    """
    permission_classes = [IsSecretaryGeneral]

    def post(self, request, pk):
        try:
            advert = Advert.objects.get(
                pk          = pk,
                association = request.user.association,
            )
        except Advert.DoesNotExist:
            return Response(
                {'detail': 'Advert not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if not advert.is_live:
            return Response(
                {'detail': 'Advert is not currently live.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        reason = request.data.get('reason', '')

        advert.status  = Advert.Status.OFFLINE
        advert.is_live = False
        advert.save()

        from notifications.utils import send_notification
        send_notification(
            user       = advert.operator,
            category   = 'adverts',
            title      = 'Advert Taken Offline',
            message    = (
                f'Your advert "{advert.headline}" has been taken offline. '
                f'{f"Reason: {reason}" if reason else ""}'
            ),
            related_id = str(advert.id),
        )

        return Response({
            'detail':   'Advert taken offline.',
            'headline': advert.headline,
            'status':   advert.status,
        })


@extend_schema(tags=['Adverts'])
class AdvertRevenueSummaryView(APIView):
    """
    GET /api/v1/adverts/revenue-summary/
    Secretary General sees advert revenue breakdown.
    """
    permission_classes = [IsSecretaryOrPresident]

    def get(self, request):
        from django.db.models import Sum, Count
        assoc = request.user.association

        approved = Advert.objects.filter(
            association = assoc,
            status__in  = [Advert.Status.APPROVED, Advert.Status.EXPIRED, Advert.Status.OFFLINE],
        )

        total_revenue   = approved.aggregate(total=Sum('fee'))['total'] or 0
        iscooa_revenue  = approved.aggregate(total=Sum('iscooa_cut'))['total'] or 0
        iprolance_rev   = approved.aggregate(total=Sum('iprolance_cut'))['total'] or 0

        by_category = {}
        for cat in Advert.Category.choices:
            code, label = cat
            cat_total = approved.filter(category=code).aggregate(
                total=Sum('fee')
            )['total'] or 0
            by_category[code] = {
                'label':       label,
                'total_naira': cat_total / 100,
                'count':       approved.filter(category=code).count(),
            }

        live_count    = Advert.objects.filter(association=assoc, is_live=True).count()
        pending_count = Advert.objects.filter(association=assoc, status='pending').count()

        return Response({
            'total_revenue_naira':    total_revenue / 100,
            'association_cut_naira':  iscooa_revenue / 100,
            'platform_cut_naira':     iprolance_rev / 100,
            'live_adverts':           live_count,
            'pending_adverts':        pending_count,
            'by_category':            by_category,
        })


# ─── HELPER FUNCTIONS ─────────────────────────────────────────────────────────

def _auto_expire_adverts(association):
    """
    Check for expired adverts and mark them offline.
    Called before every marketplace or queue query.
    """
    expired = Advert.objects.filter(
        association = association,
        status      = Advert.Status.APPROVED,
        is_live     = True,
        expires_at__lt = timezone.now(),
    )
    if expired.exists():
        expired.update(status=Advert.Status.EXPIRED, is_live=False)