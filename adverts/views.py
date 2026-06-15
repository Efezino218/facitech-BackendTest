from django.utils import timezone
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import Advert
from .serializers import (
    AdvertSerializer, AdvertCreateSerializer, AdvertListSerializer
)
from .permissions import IsOperator, IsSecretaryGeneral, IsIscooaExec
from drf_spectacular.utils import extend_schema


# ─── OPERATOR ADVERT VIEWS ────────────────────────────────────────────────────

@extend_schema(tags=['Adverts'])
class MyAdvertsView(generics.ListAPIView):
    """
    GET /api/v1/adverts/my-adverts/
    Operator sees all their advert submissions.
    Filter by ?status=pending|approved|rejected
    """
    serializer_class   = AdvertListSerializer
    permission_classes = [IsOperator]

    def get_queryset(self):
        qs = Advert.objects.filter(operator=self.request.user)
        advert_status = self.request.query_params.get('status')
        if advert_status:
            qs = qs.filter(status=advert_status)
        return qs


@extend_schema(tags=['Adverts'])
class SubmitAdvertView(generics.CreateAPIView):
    """
    POST /api/v1/adverts/submit/
    Operator submits a new advert.
    Fee is auto-set from category.
    """
    serializer_class   = AdvertCreateSerializer
    permission_classes = [IsOperator]

    def perform_create(self, serializer):
        serializer.save(operator=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        advert = serializer.save(operator=request.user)
        return Response(
            {
                'detail':       'Advert submitted successfully. Awaiting Secretary General approval.',
                'id':           str(advert.id),
                'headline':     advert.headline,
                'category':     advert.category,
                'fee_naira':    advert.fee_naira,
                'status':       advert.status,
            },
            status=status.HTTP_201_CREATED
        )


@extend_schema(tags=['Adverts'])
class MyAdvertDetailView(generics.RetrieveDestroyAPIView):
    """
    GET    /api/v1/adverts/my-adverts/<id>/
    DELETE /api/v1/adverts/my-adverts/<id>/
    Operator views or withdraws their own advert.
    Can only delete if still pending.
    """
    serializer_class   = AdvertSerializer
    permission_classes = [IsOperator]

    def get_queryset(self):
        return Advert.objects.filter(operator=self.request.user)

    def perform_destroy(self, instance):
        if instance.status != Advert.Status.PENDING:
            from rest_framework.exceptions import ValidationError
            raise ValidationError(
                'Only pending adverts can be withdrawn.'
            )
        instance.delete()


# ─── MARKETPLACE VIEW (Public — all approved live adverts) ────────────────────

@extend_schema(tags=['Adverts'])
class MarketplaceView(generics.ListAPIView):
    """
    GET /api/v1/adverts/marketplace/
    All approved live adverts visible to all operators.
    Filter by ?category=promo|new_stock|vacancy|services
    """
    serializer_class   = AdvertListSerializer
    permission_classes = [IsOperator]

    def get_queryset(self):
        qs = Advert.objects.filter(
            status  = Advert.Status.APPROVED,
            is_live = True,
        )
        category = self.request.query_params.get('category')
        if category:
            qs = qs.filter(category=category)
        return qs


# ─── SECRETARY GENERAL ADVERT VIEWS ──────────────────────────────────────────

@extend_schema(tags=['Adverts'])
class AdvertQueueView(generics.ListAPIView):
    """
    GET /api/v1/adverts/queue/
    Secretary General sees all advert submissions.
    Filter by ?status=pending|approved|rejected
    """
    serializer_class   = AdvertSerializer
    permission_classes = [IsSecretaryGeneral]

    def get_queryset(self):
        qs = Advert.objects.all()
        advert_status = self.request.query_params.get('status')
        if advert_status:
            qs = qs.filter(status=advert_status)
        return qs


@extend_schema(tags=['Adverts'])
class AdvertDetailAdminView(generics.RetrieveAPIView):
    """
    GET /api/v1/adverts/queue/<id>/
    Secretary General views full advert detail.
    """
    serializer_class   = AdvertSerializer
    permission_classes = [IsSecretaryGeneral]
    queryset           = Advert.objects.all()


@extend_schema(tags=['Adverts'])
class ApproveAdvertView(APIView):
    """
    POST /api/v1/adverts/<id>/approve/
    Secretary General approves an advert.
    Marks it live and records commission split.
    """
    permission_classes = [IsSecretaryGeneral]

    def post(self, request, pk):
        try:
            advert = Advert.objects.get(pk=pk)
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

        now = timezone.now()
        advert.status       = Advert.Status.APPROVED
        advert.is_live      = True
        advert.live_from    = now
        advert.expires_at   = now + timezone.timedelta(days=30)
        advert.reviewed_by  = request.user
        advert.reviewed_at  = now
        advert.save()

        return Response({
            'detail':           'Advert approved and now live.',
            'headline':         advert.headline,
            'fee_naira':        advert.fee_naira,
            'iscooa_cut_naira': advert.iscooa_cut_naira,
            'iprolance_cut_naira': advert.iprolance_cut_naira,
            'live_from':        advert.live_from,
            'expires_at':       advert.expires_at,
        })


@extend_schema(tags=['Adverts'])
class RejectAdvertView(APIView):
    """
    POST /api/v1/adverts/<id>/reject/
    Secretary General rejects an advert with a reason.
    """
    permission_classes = [IsSecretaryGeneral]

    def post(self, request, pk):
        try:
            advert = Advert.objects.get(pk=pk)
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

        advert.status        = Advert.Status.REJECTED
        advert.reject_reason = reject_reason
        advert.reviewed_by   = request.user
        advert.reviewed_at   = timezone.now()
        advert.save()

        return Response({
            'detail': 'Advert rejected.',
            'reason': advert.reject_reason,
        })


@extend_schema(tags=['Adverts'])
class AdvertRevenueSummaryView(APIView):
    """
    GET /api/v1/adverts/revenue-summary/
    Secretary General sees total advert revenue and commissions.
    """
    permission_classes = [IsSecretaryGeneral]

    def get(self, request):
        from django.db.models import Sum

        approved = Advert.objects.filter(status=Advert.Status.APPROVED)

        totals = approved.aggregate(
            total_fees      = Sum('fee'),
            total_iscooa    = Sum('iscooa_cut'),
            total_iprolance = Sum('iprolance_cut'),
        )

        return Response({
            'approved_adverts_count':   approved.count(),
            'total_fees_naira':         (totals['total_fees'] or 0) / 100,
            'iscooa_commission_naira':  (totals['total_iscooa'] or 0) / 100,
            'iprolance_share_naira':    (totals['total_iprolance'] or 0) / 100,
        })