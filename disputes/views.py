from urllib import request

from django.utils import timezone
from django.db import transaction
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from notifications.utils import send_notification, send_bulk_notification
from accounts.models import User

from .models import Dispute, DisputeUpdate
from .serializers import (
    DisputeSerializer, DisputeCreateSerializer,
    DisputeListSerializer, DisputeRespondSerializer,
)
from .permissions import IsOperator, IsIscooaExec
from drf_spectacular.utils import extend_schema


# ─── OPERATOR DISPUTE VIEWS ───────────────────────────────────────────────────
@extend_schema(tags=['Disputes'])
class MyDisputesView(generics.ListAPIView):
    """
    GET /api/v1/disputes/my-disputes/
    Operator sees all their raised disputes.
    Filter by ?status=open|under_review|investigating|resolved
    Filter by ?category=bill|maintenance|lift|water|security etc
    """
    serializer_class   = DisputeListSerializer
    permission_classes = [IsOperator]

    def get_queryset(self):
        qs = Dispute.objects.filter(operator=self.request.user)
        dispute_status = self.request.query_params.get('status')
        if dispute_status:
            qs = qs.filter(status=dispute_status)
        category = self.request.query_params.get('category')
        if category:
            qs = qs.filter(category=category)
        return qs

@extend_schema(tags=['Disputes'])
class RaiseDisputeView(generics.CreateAPIView):
    """
    POST /api/v1/disputes/raise/
    Operator raises a new dispute or facility issue.
    """
    serializer_class   = DisputeCreateSerializer
    permission_classes = [IsOperator]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        dispute = serializer.save(operator=request.user)

        # Notify all exco members about new dispute
        exco_users = User.objects.filter(
            role        = 'is',
            association = request.user.association,
            is_active   = True,
        )
        send_bulk_notification(
            users      = exco_users,
            category   = 'disputes',
            title      = f'New Dispute Raised — {dispute.dispute_ref}',
            message    = (
                f'Operator {request.user.full_name or request.user.email} '
                f'has raised a {dispute.get_category_display()} dispute: '
                f'"{dispute.subject}". Priority: {dispute.get_priority_display()}.'
            ),
            related_id = str(dispute.id),
        )
        return Response(
            {
                'detail':       'Dispute raised successfully. ISCOOA will review within 48 hours.',
                'dispute_ref':  dispute.dispute_ref,
                'subject':      dispute.subject,
                'category':     dispute.category,
                'status':       dispute.status,
            },
            status=status.HTTP_201_CREATED
        )


@extend_schema(tags=['Disputes'])
class MyDisputeDetailView(generics.RetrieveAPIView):
    """
    GET /api/v1/disputes/my-disputes/<id>/
    Operator views full detail of their dispute
    including the full update timeline.
    """
    serializer_class   = DisputeSerializer
    permission_classes = [IsOperator]

    def get_queryset(self):
        return Dispute.objects.filter(operator=self.request.user)


# ─── ISCOOA EXECUTIVE DISPUTE VIEWS ──────────────────────────────────────────

@extend_schema(tags=['Disputes'])
class AllDisputesView(generics.ListAPIView):
    """
    GET /api/v1/disputes/all/
    ISCOOA Executive sees all disputes.
    Filter by ?status=open|under_review|investigating|resolved
    Filter by ?category=bill|maintenance|lift|water|security etc
    Filter by ?priority=low|medium|high|urgent
    """
    serializer_class   = DisputeListSerializer
    permission_classes = [IsIscooaExec]

    def get_queryset(self):
        qs = Dispute.objects.filter(
            operator__association = self.request.user.association
        )
        dispute_status = self.request.query_params.get('status')
        if dispute_status:
            qs = qs.filter(status=dispute_status)
        category = self.request.query_params.get('category')
        if category:
            qs = qs.filter(category=category)
        priority = self.request.query_params.get('priority')
        if priority:
            qs = qs.filter(priority=priority)
        return qs


@extend_schema(tags=['Disputes'])
class DisputeDetailAdminView(generics.RetrieveAPIView):
    """
    GET /api/v1/disputes/all/<id>/
    ISCOOA Executive views full dispute detail.
    """
    serializer_class   = DisputeSerializer
    permission_classes = [IsIscooaExec]

    def get_queryset(self):
        return Dispute.objects.filter(
            operator__association = self.request.user.association
        )


@extend_schema(tags=['Disputes'])
class RespondToDisputeView(APIView):
    """
    POST /api/v1/disputes/<id>/respond/
    ISCOOA Executive updates dispute status and adds a response.
    Every update is logged in the DisputeUpdate timeline.
    """
    permission_classes = [IsIscooaExec]

    def post(self, request, pk):
        try:
            dispute = Dispute.objects.get(
                pk = pk,
                operator__association = request.user.association,
            )
        except Dispute.DoesNotExist:
            return Response(
                {'detail': 'Dispute not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = DisputeRespondSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        new_status  = serializer.validated_data['new_status']
        response    = serializer.validated_data['response']
        note        = serializer.validated_data.get('note', '')

        old_status  = dispute.status

        with transaction.atomic():
            dispute.status      = new_status
            dispute.response    = response
            dispute.assigned_to = request.user

            if new_status == Dispute.Status.RESOLVED:
                dispute.resolved_at = timezone.now()

            dispute.save()

            # Notify operator about the dispute update
            send_notification(
                user       = dispute.operator,
                category   = 'disputes',
                title      = f'Dispute Update — {dispute.dispute_ref}',
                message    = (
                    f'Your dispute "{dispute.subject}" has been updated. '
                    f'New status: {dispute.get_status_display()}. '
                    f'Response: {response}'
                ),
                related_id = str(dispute.id),
            )

            DisputeUpdate.objects.create(
                dispute    = dispute,
                updated_by = request.user,
                old_status = old_status,
                new_status = new_status,
                note       = note or response,
            )

        return Response({
            'detail':       'Dispute updated successfully.',
            'dispute_ref':  dispute.dispute_ref,
            'old_status':   old_status,
            'new_status':   dispute.status,
            'response':     dispute.response,
        })


@extend_schema(tags=['Disputes'])
class DisputeStatsView(APIView):
    """
    GET /api/v1/disputes/stats/
    ISCOOA Executive sees dispute statistics.
    """
    permission_classes = [IsIscooaExec]

    def get(self, request):
        from django.db.models import Count

        qs = Dispute.objects.filter(
            operator__association = request.user.association
        )
        total       = qs.count()
        by_status   = qs.values('status').annotate(count=Count('id'))
        by_category = qs.values('category').annotate(count=Count('id'))
        by_priority = qs.values('priority').annotate(count=Count('id'))

        return Response({
            'total_disputes':   total,
            'by_status':        {item['status']: item['count'] for item in by_status},
            'by_category':      {item['category']: item['count'] for item in by_category},
            'by_priority':      {item['priority']: item['count'] for item in by_priority},
        })